import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session
from app.core.websocket import manager
from app.modules.direcciones.schemas import DireccionPublic
from app.modules.pedido.models import DetallePedido, HistorialEstadoPedido, Pedido
from app.modules.pedido.schemas import ( AvanzarEstadoRequest, CrearPedidoRequest, DetallePedidoRead, DireccionSnapshot, HistorialEstadoRead, PagoRead, PaginatedPedidos, PedidoDetail, PedidoRead)
from app.modules.pedido.unit_of_work import PedidoUnitOfWork
from app.modules.producto.service import ProductoService
from app.modules.usuarios.schemas import UserPublic

FORMAS_PAGO_CON_ENVIO = {"MERCADOPAGO"}

ESTADO = {
    "PENDIENTE": "PENDIENTE",
    "CONFIRMADO": "CONFIRMADO",
    "EN_PREPARACION": "EN_PREPARACION",
    "EN_CAMINO": "EN_CAMINO",
    "ENTREGADO": "ENTREGADO",
    "CANCELADO": "CANCELADO",
}

_FACTORES = {
    ("kg", "g"): Decimal("1000"),
    ("g", "kg"): Decimal("0.001"),
    ("l", "ml"): Decimal("1000"),
    ("ml", "l"): Decimal("0.001"),
}


TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    ESTADO["PENDIENTE"]: {ESTADO["CONFIRMADO"], ESTADO["CANCELADO"]},
    ESTADO["CONFIRMADO"]: {ESTADO["EN_PREPARACION"], ESTADO["CANCELADO"]},
    ESTADO["EN_PREPARACION"]: {ESTADO["EN_CAMINO"], ESTADO["CANCELADO"]},
    ESTADO["EN_CAMINO"]: {ESTADO["ENTREGADO"]},
    ESTADO["ENTREGADO"]: set(),
    ESTADO["CANCELADO"]: set(),
}

PERMISOS_TRANSICION: dict[tuple[str, str], set[str] | None] = {
    (ESTADO["PENDIENTE"], ESTADO["CONFIRMADO"]): None,
    (ESTADO["PENDIENTE"], ESTADO["CANCELADO"]): {"CLIENT", "PEDIDOS", "ADMIN"},
    (ESTADO["CONFIRMADO"], ESTADO["EN_PREPARACION"]): {"PEDIDOS", "ADMIN"},
    (ESTADO["CONFIRMADO"], ESTADO["CANCELADO"]): {"PEDIDOS", "ADMIN"},
    (ESTADO["EN_PREPARACION"], ESTADO["EN_CAMINO"]): {"PEDIDOS", "ADMIN"},
    (ESTADO["EN_PREPARACION"], ESTADO["CANCELADO"]): {"ADMIN"},
    (ESTADO["EN_CAMINO"], ESTADO["ENTREGADO"]): {"PEDIDOS", "ADMIN"},
}

ESTADOS_CANCELABLES_POR_CLIENTE = {ESTADO["PENDIENTE"], ESTADO["CONFIRMADO"]}

EVENTOS_WS = {
    "PENDIENTE":      "NUEVO_PEDIDO",
    "CONFIRMADO":     "PEDIDO_CONFIRMADO",
    "EN_PREPARACION": "PEDIDO_EN_PREPARACION",
    "EN_CAMINO":      "PEDIDO_EN_CAMINO",
    "ENTREGADO":      "PEDIDO_ENTREGADO",
    "CANCELADO":      "PEDIDO_CANCELADO",
}

logger = logging.getLogger(__name__)

class PedidoService:

    def __init__(self, session: Session) -> None:
        self._session = session
        self._producto_service = ProductoService(session)

    # ── Helpers Publicos ──────────────────────────────────────────────────────

    def pedido_pertenece_a_usuario(self, pedido_id: int, usuario_id: int) -> bool:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id(pedido_id)

            return pedido is not None and pedido.usuario_id == usuario_id

    # ── Helpers privados ──────────────────────────────────────────────────────
  
    def _get_or_404(self, uow: PedidoUnitOfWork, pedido_id: int) -> Pedido:
        pedido = uow.pedidos.get_by_id(pedido_id)

        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido con id={pedido_id} no encontrado",
            )
        
        return pedido


    def _puede_ver_pedido(self, usuario: UserPublic, pedido: Pedido) -> bool:
        roles = {r.upper() for r in usuario.roles}

        if roles & {"ADMIN", "PEDIDOS"}:
            return True

        return pedido.usuario_id == usuario.id


    def _validar_forma_pago(self, forma_pago_codigo: str, uow: PedidoUnitOfWork) -> None:
        forma_pago = uow.formas_pago.get_by_id(forma_pago_codigo)

        if not forma_pago:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forma de pago '{forma_pago_codigo}' no encontrada",
            )

        if not forma_pago.habilitado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La forma de pago '{forma_pago_codigo}' no está habilitada",
            )
        
        
    def _validar_direccion_requerida(self, forma_pago_codigo: str, direccion_id: Optional[int]) -> None:
        if forma_pago_codigo in FORMAS_PAGO_CON_ENVIO and direccion_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"La forma de pago '{forma_pago_codigo}' requiere una dirección de entrega.",
            )


    def _convertir_unidad_ing(self, cantidad: Decimal, origen: str, destino: str) -> Decimal:
        if origen == destino:
            return cantidad
        factor = _FACTORES.get((origen, destino))
        if factor is None:
            raise HTTPException(
                status_code=422,
                detail=f"No existe conversión entre '{origen}' y '{destino}'",
            )
        return cantidad * factor


    def _validar_y_construir_detalles(self, items: list, uow: PedidoUnitOfWork) -> list[dict]:
        ids = [i.producto_id for i in items]

        if len(ids) != len(set(ids)):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Hay productos repetidos en el pedido; consolidá las cantidades.",
            )

        detalles_data = []

        for item in items:
            producto = uow.productos.get_with_lock(item.producto_id)

            if producto is None or producto.deleted_at is not None:
                raise HTTPException(404, f"Producto {item.producto_id} no encontrado.")

            if not producto.disponible:
                raise HTTPException(400, f"'{producto.nombre}' no está disponible.")

            if producto.stock_cantidad < item.cantidad:
                raise HTTPException(
                    400,
                    f"Stock insuficiente para '{producto.nombre}'. "
                    f"Disponible: {producto.stock_cantidad}, solicitado: {item.cantidad}.",
                )

            if item.personalizacion:
                removibles = uow.productos.get_removibles_ids(producto.id)
                invalidos = set(item.personalizacion) - removibles

                if invalidos:
                    raise HTTPException(
                        422,
                        f"Ingredientes no removibles o ajenos a '{producto.nombre}': {sorted(invalidos)}",
                    )

            detalles_data.append({
                "producto_id":     producto.id,
                "nombre_snapshot": producto.nombre,
                "cantidad":        item.cantidad,
                "precio_snapshot": producto.precio_base,
                "subtotal_snap":   producto.precio_base * item.cantidad,
                "personalizacion": item.personalizacion,
            })

        return detalles_data


    def _descontar_stock_pedido(self, uow: PedidoUnitOfWork, pedido: Pedido) -> None:
        for detalle in pedido.detalles:
            producto = uow.productos.get_with_lock(detalle.producto_id)
            if not producto:
                continue

            producto.stock_cantidad -= detalle.cantidad
            logger.info(
                "Stock producto descontado: producto=%s nuevo_stock=%s",
                producto.id, producto.stock_cantidad,
            )
            uow.productos.add(producto)

            if not producto.es_producto_final:
                removidos = set(detalle.personalizacion or [])

                for pi in producto.producto_ingredientes:
                    if pi.ingrediente_id in removidos:
                        logger.info(
                            "Ingrediente removido por personalización, se omite descuento: ingrediente=%s",
                            pi.ingrediente_id,
                        )
                        continue

                    ingrediente = uow.ingredientes.get_with_lock(pi.ingrediente_id)
                    if not ingrediente:
                        continue

                    unidad_ingrediente = uow.productos.get_unidad_medida(ingrediente.unidad_medida_id)
                    unidad_receta = uow.productos.get_unidad_medida(pi.unidad_medida_id)

                    if not unidad_ingrediente or not unidad_receta:
                        continue

                    cantidad_receta = Decimal(str(pi.cantidad)) * detalle.cantidad
                    cantidad_convertida = self._convertir_unidad_ing(
                        cantidad_receta,
                        unidad_receta.simbolo,
                        unidad_ingrediente.simbolo,
                    )

                    ingrediente.stock_cantidad -= cantidad_convertida
                    logger.info(
                        "Stock ingrediente descontado: ingrediente=%s nuevo_stock=%s",
                        ingrediente.id, ingrediente.stock_cantidad,
                    )
                    uow.ingredientes.add(ingrediente)


    def _validar_direccion(self, direccion_id: int, usuario_id: int, uow: PedidoUnitOfWork) -> None:
        direccion: DireccionPublic = uow.direcciones.get_by_id(direccion_id)

        if not direccion or direccion.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dirección {direccion_id} no encontrada",
            )
        
        if direccion.usuario_id != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La dirección no pertenece al usuario",
            )


    def _to_pedido_detail(self, pedido: Pedido) -> PedidoDetail:
        return PedidoDetail(
            id=pedido.id,
            estado_codigo=pedido.estado_codigo,
            subtotal=pedido.subtotal,
            descuento=pedido.descuento,
            costo_envio=pedido.costo_envio,
            total=pedido.total,
            created_at=pedido.created_at,
            usuario_id=pedido.usuario_id,
            direccion_id=pedido.direccion_id,
            forma_pago_codigo=pedido.forma_pago_codigo,
            notas=pedido.notas,
            actualizado_en=pedido.updated_at,
            estado=pedido.estado,
            forma_pago=pedido.forma_pago,
            usuario=pedido.usuario,
            direccion=pedido.direccion,
            direccion_snapshot=(
                DireccionSnapshot.model_validate(pedido.direccion, from_attributes=True)
                if pedido.direccion else None
            ),
            detalles=[
                DetallePedidoRead(
                    producto_id=d.producto_id,
                    nombre_snapshot=d.nombre_snapshot,
                    cantidad=d.cantidad,
                    precio_snapshot=d.precio_snapshot,
                    subtotal_snap=d.subtotal_snap,
                    personalizacion=d.personalizacion,
                )
                for d in pedido.detalles
            ],
            historial_estados=[
                HistorialEstadoRead.model_validate(h)
                for h in sorted(pedido.historial, key=lambda h: h.created_at)
            ],
            pagos=[
                PagoRead(
                    id=p.id,
                    monto=p.transaction_amount,     
                    mp_payment_id=p.mp_payment_id,
                    mp_status=p.mp_status,
                    creado_en=p.created_at,
                )
                for p in pedido.pagos
            ],
        )


    def _to_pedido_read(self, pedido: Pedido) -> PedidoRead:
        cantidad_items = sum(d.cantidad for d in pedido.detalles) if pedido.detalles else None
        cliente_nombre = None
        cliente_email = None
        if pedido.usuario:
            cliente_nombre = f"{pedido.usuario.nombre} {pedido.usuario.apellido}".strip()
            cliente_email = pedido.usuario.email

        return PedidoRead(
            id=pedido.id,
            estado_codigo=pedido.estado_codigo,
            subtotal=pedido.subtotal,
            descuento=pedido.descuento,
            costo_envio=pedido.costo_envio,
            total=pedido.total,
            created_at=pedido.created_at,
            cantidad_items=cantidad_items,
            cliente_nombre=cliente_nombre,
            cliente_email=cliente_email,
        )


    def _calcular_costo_envio(self, subtotal: Decimal) -> Decimal:
        return Decimal("500")


    async def _emit_ws(
            self,
            *,
            pedido_id: int,
            dueno_id: int,
            estado_anterior: Optional[str],
            estado_nuevo: str,
            usuario_id: Optional[int],      
            motivo: Optional[str] = None,
            event: Optional[str] = None,    
        ) -> None:
            if event is None:
                event = (
                    "pedido_cancelado"
                    if estado_nuevo == ESTADO["CANCELADO"]
                    else "estado_cambiado"
                )

            evento = {
                "event": event,
                "pedido_id": pedido_id,
                "estado_anterior": estado_anterior,
                "estado_nuevo": estado_nuevo,
                "usuario_id": usuario_id,
                "motivo": motivo,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

            try:
                await manager.broadcast_pedido(pedido_id=pedido_id, dueno_id=dueno_id, evento=evento)
            except Exception:
                logger.exception("Fallo emitiendo WS para pedido %s", pedido_id)


    def _aplicar_transicion(
        self,
        uow: PedidoUnitOfWork,
        pedido: Pedido,
        destino: str,
        usuario_id: Optional[int],
        motivo: Optional[str],
    ) -> None:
        estado_actual = pedido.estado_codigo

        if destino == ESTADO["CONFIRMADO"] and estado_actual == ESTADO["PENDIENTE"]:
            self._descontar_stock_pedido(uow, pedido)

        if destino == ESTADO["CANCELADO"] and estado_actual != ESTADO["PENDIENTE"]:
            for detalle in pedido.detalles:
                producto = uow.productos.get_with_lock(detalle.producto_id)
                if not producto:
                    continue

                producto.stock_cantidad += detalle.cantidad
                uow.productos.add(producto)

                if not producto.es_producto_final:
                    removidos = set(detalle.personalizacion or [])

                    for pi in producto.producto_ingredientes:
                        if pi.ingrediente_id in removidos:
                            logger.info(
                                "Ingrediente removido por personalización, se omite devolución: ingrediente=%s",
                                pi.ingrediente_id,
                            )
                            continue

                        ingrediente = uow.ingredientes.get_with_lock(pi.ingrediente_id)
                        if not ingrediente:
                            continue

                        unidad_ingrediente = uow.productos.get_unidad_medida(ingrediente.unidad_medida_id)
                        unidad_receta = uow.productos.get_unidad_medida(pi.unidad_medida_id)

                        if not unidad_ingrediente or not unidad_receta:
                            continue

                        cantidad_receta = Decimal(str(pi.cantidad)) * detalle.cantidad
                        cantidad_convertida = self._convertir_unidad_ing(
                            cantidad_receta,
                            unidad_receta.simbolo,
                            unidad_ingrediente.simbolo,
                        )

                        ingrediente.stock_cantidad += cantidad_convertida
                        logger.info(
                            "Stock ingrediente devuelto: ingrediente=%s nuevo_stock=%s",
                            ingrediente.id, ingrediente.stock_cantidad,
                        )
                        uow.ingredientes.add(ingrediente)

        pedido.estado_codigo = destino
        pedido.updated_at = datetime.now(timezone.utc)
        uow.pedidos.add(pedido)

        uow.historial.add(HistorialEstadoPedido(
            pedido_id=pedido.id,
            estado_desde=estado_actual,
            estado_hacia=destino,
            usuario_id=usuario_id,
            motivo=motivo,
        ))

        logger.info(
            "FSM: usuario=%s pedido=%s '%s' → '%s'",
            usuario_id, pedido.id, estado_actual, destino,
        )

    #──────────────────────────────────────────────────────

    async def crear_pedido(self, usuario_id: int, data: CrearPedidoRequest) -> PedidoRead:
        with PedidoUnitOfWork(self._session) as uow:
            self._validar_forma_pago(data.forma_pago_codigo, uow)
            self._validar_direccion_requerida(data.forma_pago_codigo, data.direccion_id)

            if  data.direccion_id is not None:
                self._validar_direccion(data.direccion_id, usuario_id, uow)
                
            
            detalles_data = self._validar_y_construir_detalles(data.items, uow)

            subtotal = sum(i["subtotal_snap"] for i in detalles_data)
            costo_envio = (
                self._calcular_costo_envio(subtotal)
                if data.direccion_id is not None
                else Decimal("0")
            )

            total = subtotal + costo_envio

            pedido = uow.pedidos.add(Pedido(
                usuario_id=usuario_id,
                estado_codigo=ESTADO["PENDIENTE"],
                direccion_id=data.direccion_id,
                forma_pago_codigo=data.forma_pago_codigo,
                subtotal=subtotal,
                costo_envio=costo_envio,
                total=total,
                notas=data.notas,
            ))

            uow.detalles.add_all([DetallePedido(pedido_id=pedido.id, **item) for item in detalles_data])

            uow.historial.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde=None,   
                    estado_hacia=ESTADO["PENDIENTE"],
                    usuario_id=usuario_id,
                    motivo="Pedido creado",             
                )
            )

            result = self._to_pedido_read(pedido)

        await self._emit_ws(
                pedido_id=result.id, dueno_id=usuario_id,
                estado_anterior=None, estado_nuevo=ESTADO["PENDIENTE"],
                usuario_id=usuario_id, motivo="Pedido creado",
            )

        return result
  

    def obtener_pedidos(
        self,
        usuario: UserPublic,
        estado: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> PaginatedPedidos:
        usuario_id = usuario.id

        if {"PEDIDOS", "ADMIN"} & {r.upper() for r in usuario.roles}:
            usuario_id = None

        with PedidoUnitOfWork(self._session) as uow:
            pedidos = uow.pedidos.get_all_pedidos(
                usuario_id=usuario_id,
                estado=estado,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                offset=offset,
                limit=limit,
            )

            total = uow.pedidos.count_all_pedidos(
                usuario_id=usuario_id,
                estado=estado,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )

            return PaginatedPedidos(
                items=[self._to_pedido_read(p) for p in pedidos],
                 total=total,
            )   
        

    def obtener_pedido(self, pedido_id: int, usuario: UserPublic) -> PedidoDetail:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)

            if not self._puede_ver_pedido(usuario, pedido):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tenés permiso para ver este pedido",
                )

            return self._to_pedido_detail(pedido)
        

    async def avanzar_pedido(self, pedido_id: int, data: AvanzarEstadoRequest, usuario: UserPublic) -> PedidoRead:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            destino = data.nuevo_estado
            origen = pedido.estado_codigo

            if destino not in TRANSICIONES_VALIDAS.get(origen, set()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Transición inválida: '{origen}' → '{destino}'.",
                )

            roles = {r.upper().strip() for r in usuario.roles}
            roles_permitidos = PERMISOS_TRANSICION.get((origen, destino))
 
            if roles_permitidos is not None and not (roles & roles_permitidos):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No tenés permiso para la transición '{origen}' → '{destino}'.",
                )
            
            self._aplicar_transicion(uow, pedido, destino, usuario.id, data.motivo)
            
            result = self._to_pedido_read(pedido)
            dueno_id = pedido.usuario_id

            await self._emit_ws(
                pedido_id=result.id, dueno_id=dueno_id,
                estado_anterior=origen, estado_nuevo=destino,
                usuario_id=usuario.id, motivo=data.motivo,
            )

        return result
        

# consultar
    async def cancelar_pedido(self, pedido_id: int, observacion: Optional[str], usuario: UserPublic) -> PedidoDetail:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)

            estado_actual = pedido.estado_codigo

            if ESTADO["CANCELADO"] not in TRANSICIONES_VALIDAS.get(estado_actual, set()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El pedido en estado '{estado_actual}' no puede cancelarse.",
                )

            roles_permitidos = PERMISOS_TRANSICION.get((estado_actual, ESTADO["CANCELADO"]))
            roles = {r.upper().strip() for r in usuario.roles}

            if roles_permitidos is not None and not (roles & roles_permitidos):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No tenés permiso para cancelar un pedido "
                           f"en estado '{estado_actual}'.",
                )
            
            es_staff = bool(roles & {"PEDIDOS", "ADMIN"})

            if not es_staff and pedido.usuario_id != usuario.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tenés permiso para cancelar este pedido.",
                )
 
            self._aplicar_transicion(
                uow, pedido, ESTADO["CANCELADO"], usuario.id, observacion
            )
 
            result = self._to_pedido_detail(pedido)
            dueno_id = pedido.usuario_id
 
        await self._emit_ws(
            pedido_id=result.id,
            dueno_id=dueno_id,
            estado_anterior=estado_actual,
            estado_nuevo=ESTADO["CANCELADO"],
            usuario_id=usuario.id,
            motivo=observacion,
            event=EVENTOS_WS[ESTADO["CANCELADO"]],
        )
        return result
        

    def obtener_historial_pedido(self, pedido_id: int, usuario: UserPublic) -> list[HistorialEstadoRead]:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)

            if not self._puede_ver_pedido(usuario, pedido):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tenés permiso para ver el historial de este pedido",
                )

            historial = sorted(pedido.historial, key=lambda h: h.created_at)

            return [HistorialEstadoRead.model_validate(h) for h in historial]
        

    async def cancelar_pedido_propio(self, pedido_id, usuario, motivo=None) -> PedidoRead:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)

            if pedido.usuario_id != usuario.id:
                raise HTTPException(403, "Solo podés cancelar tus propios pedidos")

            if pedido.estado_codigo not in ESTADOS_CANCELABLES_POR_CLIENTE:
                raise HTTPException(
                    400,
                    f"Un pedido en estado '{pedido.estado_codigo}' ya no puede cancelarse desde el cliente.",
                )
            estado_anterior = pedido.estado_codigo
            
            self._aplicar_transicion(
                uow, pedido, ESTADO["CANCELADO"], usuario.id,
                motivo or "Cancelado por el cliente",
            )

            result = self._to_pedido_read(pedido)
            dueno_id = pedido.usuario_id

            await self._emit_ws(
                pedido_id=result.id, dueno_id=dueno_id,
                estado_anterior=estado_anterior, estado_nuevo=ESTADO["CANCELADO"],
                usuario_id=usuario.id, motivo=motivo or "Cancelado por el cliente",
            )
        return result
        
    async def confirmar_por_pago(self, pedido_id: int) -> None:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_with_lock(pedido_id)

            if not pedido:
                return

            if pedido.estado_codigo != ESTADO["PENDIENTE"]:
                return

            self._aplicar_transicion(
                uow, pedido, ESTADO["CONFIRMADO"],
                usuario_id=None,
                motivo="Pago aprobado por MercadoPago",
            )

            dueno_id = pedido.usuario_id

        await self._emit_ws(
            pedido_id=pedido_id,
            dueno_id=dueno_id,
            estado_anterior=ESTADO["PENDIENTE"],
            estado_nuevo=ESTADO["CONFIRMADO"],
            usuario_id=None,
            motivo="Pago aprobado por MercadoPago",
            event=EVENTOS_WS["CONFIRMADO"],
        )