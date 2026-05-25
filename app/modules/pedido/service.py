from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.direcciones.schemas import DireccionPublic
from app.modules.pedido.models import DetallePedido, HistorialEstadoPedido, Pedido
from app.modules.pedido.schemas import DetallePedidoRead, DireccionSnapshot, PedidoCreate, PedidoDetail, PedidoListResponse, PedidoListResponse
from app.modules.pedido.unit_of_work import PedidoUnitOfWork
from app.modules.producto.models import Producto
from app.modules.producto.service import ProductoService
from app.modules.usuarios.schemas import UserPublic

ESTADO = {
    "PENDIENTE": "PENDIENTE",
    "CONFIRMADO": "CONFIRMADO",
    "EN_PREPARACION": "EN_PREPARACION",
    "EN_CAMINO": "EN_CAMINO",
    "ENTREGADO": "ENTREGADO",
    "CANCELADO": "CANCELADO",
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

ESTADOS_CON_STOCK_DECREMENTADO = {
    ESTADO["CONFIRMADO"],
    ESTADO["EN_PREPARACION"],
    ESTADO["EN_CAMINO"],
}

class PedidoService:

    def __init__(self, session: Session) -> None:
        self._session = session
        self._producto_service = ProductoService(session)

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _validar_y_construir_detalles(self, items: list, uow: PedidoUnitOfWork) -> list[dict]:
        detalles_data = []

        for item in items:
            producto_locked = uow.productos.get_with_lock(item.producto_id)

            if producto_locked is None or producto_locked.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto con id {item.producto_id} no encontrado."
                )
            
            if not producto_locked.disponible:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El producto '{producto_locked.nombre}' no está disponible."
                )
            
            if producto_locked.stock_cantidad  < item.cantidad:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente para '{producto_locked.nombre}'. "
                    f"Disponible: {producto_locked.stock_cantidad}, solicitado: {item.cantidad}."
                )
            
            precio_snapshot: Decimal = producto_locked.precio_base
            subtotal = precio_snapshot * item.cantidad

            producto_locked.stock_cantidad -= item.cantidad
            uow.productos.add(producto_locked)

            detalles_data.append({
                "producto_id":      producto_locked.id,
                "nombre_snapshot":  producto_locked.nombre,   
                "cantidad":         item.cantidad,
                "precio_snapshot":  precio_snapshot,
                "subtotal_snap":    subtotal,                 
                "personalizacion":  item.personalizacion,
            })            

        return detalles_data

    def _to_pedido_detail(self, pedido: Pedido) -> PedidoDetail:
        return PedidoDetail(
            id=pedido.id,
            usuario_id=pedido.usuario_id,
            direccion_id=pedido.direccion_id,
            estado_codigo=pedido.estado_codigo,
            forma_pago_codigo=pedido.forma_pago_codigo,
            subtotal=pedido.subtotal,
            descuento=pedido.descuento,
            costo_envio=pedido.costo_envio,
            total=pedido.total,
            notas=pedido.notas,
            creado_en=pedido.created_at,
            actualizado_en=pedido.updated_at,
            estado=pedido.estado,
            forma_pago=pedido.forma_pago,
            usuario=pedido.usuario,
            direccion=pedido.direccion,
            direccion_snapshot=(
                DireccionSnapshot.model_validate(pedido.direccion, from_attributes=True)
                if pedido.direccion else None
            ),
            historial_estados=pedido.historial,
            pagos=[],
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
        )


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


    def _calcular_costo_envio(self, subtotal: Decimal) -> Decimal:
        UMBRAL_ENVIO_GRATIS = Decimal("10000")
        COSTO_ENVIO_FIJO    = Decimal("500")
        
        return Decimal("0") if subtotal >= UMBRAL_ENVIO_GRATIS else COSTO_ENVIO_FIJO


    #──────────────────────────────────────────────────────

    def crear_pedido(self, usuario_id: int, data: PedidoCreate) -> PedidoDetail:
        with PedidoUnitOfWork(self._session) as uow:
            self._validar_forma_pago(data.forma_pago_codigo, uow)

            if  data.direccion_id is not None:
                self._validar_direccion(data.direccion_id, usuario_id, uow)
                
            detalles_data = self._validar_y_construir_detalles(data.items, uow)

            subtotal = sum(i["subtotal_snap"] for i in detalles_data)
            costo_envio = self._calcular_costo_envio(subtotal)
            total = subtotal + costo_envio

            pedido = uow.pedidos.add(Pedido(
                usuario_id=usuario_id,
                estado_codigo=ESTADO["PENDIENTE"],
                direccion_id=data.direccion_id,
                forma_pago_codigo=data.forma_pago_codigo,
                subtotal=subtotal,
                costo_envio=costo_envio,
                total=total,
            ))

            uow.detalles.add_all([DetallePedido(pedido_id=pedido.id, **item) for item in detalles_data])

            uow.historial.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde=ESTADO["PENDIENTE"],   
                    estado_hacia=None,
                    usuario_id=usuario_id,
                    motivo="Pedido creado",             
                )
            )

            return self._to_pedido_detail(pedido)
        

    def obtener_pedidos(
        self,
        usuario: UserPublic,
        estado: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> PedidoListResponse:
        usuario_id = usuario.id

        if any(r in {"PEDIDOS", "ADMIN"} for r in usuario.roles):
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

            return PedidoListResponse(
                items=[self._to_pedido_detail(p) for p in pedidos],
                 total=total,
            )   
        

    def obtener_pedido(self, pedido_id: int, usuario: UserPublic) -> PedidoDetail:
        with PedidoUnitOfWork(self._session) as uow:
            rol_permitido = any(r in {"PEDIDOS", "ADMIN"} for r in usuario.roles)

            if not rol_permitido and pedido.usuario_id != usuario.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tenés permiso para ver este pedido",
                )
        
            pedido = uow.pedidos.get_by_id(pedido_id)

            if pedido is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pedido {pedido_id} no encontrado",
                )

            return self._to_pedido_detail(pedido)
        

    def avanzar_pedido(self, pedido_id: int, observacion: Optional[str], usuario: UserPublic) -> PedidoDetail:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id(pedido_id)

            if pedido is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pedido {pedido_id} no encontrado",
                )

            estado_actual = pedido.estado_codigo
            transiciones = TRANSICIONES_VALIDAS.get(estado_actual, set())

            if not transiciones:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El pedido en estado '{estado_actual}' no puede avanzar.",
                )

            nuevo_estado = next(iter(transiciones - {ESTADO["CANCELADO"]}), None)

            if nuevo_estado is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No hay un estado siguiente válido desde '{estado_actual}'.",
                )

            roles_permitidos = PERMISOS_TRANSICION.get((estado_actual, nuevo_estado))

            if roles_permitidos is not None:
                tiene_permiso = any(r in roles_permitidos for r in usuario.roles)

                if not tiene_permiso:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"No tenés permiso para avanzar de '{estado_actual}' a '{nuevo_estado}'.",
                    )

            pedido.estado_codigo = nuevo_estado
            pedido.updated_at = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

            uow.historial.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde=estado_actual,
                    estado_hacia=nuevo_estado,
                    usuario_id=usuario.id,
                    motivo=observacion,
                )
            )

            return self._to_pedido_detail(pedido)
        

    def cancelar_pedido(self, pedido_id: int, observacion: Optional[str], usuario: UserPublic) -> PedidoDetail:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id(pedido_id)

            if pedido is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pedido {pedido_id} no encontrado",
                )

            estado_actual = pedido.estado_codigo

            if ESTADO["CANCELADO"] not in TRANSICIONES_VALIDAS.get(estado_actual, set()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El pedido en estado '{estado_actual}' no puede cancelarse.",
                )

            roles_permitidos = PERMISOS_TRANSICION.get((estado_actual, ESTADO["CANCELADO"]))

            if roles_permitidos is not None:
                if not any(r in roles_permitidos for r in usuario.roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"No tenés permiso para cancelar un pedido en estado '{estado_actual}'.",
                    )

            rol_permitido = any(r in {"PEDIDOS", "ADMIN"} for r in usuario.roles)

            if not rol_permitido and pedido.usuario_id != usuario.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tenés permiso para cancelar este pedido.",
                )

            pedido.estado_codigo = ESTADO["CANCELADO"]
            pedido.updated_at = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

            uow.historial.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde=estado_actual,
                    estado_hacia=ESTADO["CANCELADO"],
                    usuario_id=usuario.id,
                    motivo=observacion,
                )
            )

            return self._to_pedido_detail(pedido)