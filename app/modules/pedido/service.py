from decimal import Decimal

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.direcciones.model import DireccionEntrega
from app.modules.direcciones.schemas import DireccionPublic
from app.modules.direcciones.service import DireccionService
from app.modules.pedido.models import DetallePedido, HistorialEstadoPedido, Pedido
from app.modules.pedido.schemas import DetallePedidoCreate, ItemPedidoRequest, PedidoCreate, PedidoDetail, PedidoRead
from app.modules.pedido.unit_of_work import PedidoUnitOfWork
from app.modules.producto.models import Producto
from app.modules.producto.service import ProductoService

ESTADO = {
    "PENDIENTE":      "PENDIENTE",
    "CONFIRMADO":     "CONFIRMADO",
    "EN_PREPARACION": "EN_PREPARACION",
    "EN_CAMINO":      "EN_CAMINO",
    "ENTREGADO":      "ENTREGADO",
    "CANCELADO":      "CANCELADO",
}

TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    ESTADO["PENDIENTE"]:      {ESTADO["CONFIRMADO"], ESTADO["CANCELADO"]},
    ESTADO["CONFIRMADO"]:     {ESTADO["EN_PREPARACION"], ESTADO["CANCELADO"]},
    ESTADO["EN_PREPARACION"]: {ESTADO["EN_CAMINO"], ESTADO["CANCELADO"]},
    ESTADO["EN_CAMINO"]:      {ESTADO["ENTREGADO"]},
    ESTADO["ENTREGADO"]:      set(),
    ESTADO["CANCELADO"]:      set(),
}

PERMISOS_TRANSICION: dict[tuple[str, str], set[str] | None] = {
    (ESTADO["PENDIENTE"],      ESTADO["CONFIRMADO"]):     None,
    (ESTADO["PENDIENTE"],      ESTADO["CANCELADO"]):      {"CLIENT", "PEDIDOS", "ADMIN"},
    (ESTADO["CONFIRMADO"],     ESTADO["EN_PREPARACION"]): {"PEDIDOS", "ADMIN"},
    (ESTADO["CONFIRMADO"],     ESTADO["CANCELADO"]):      {"PEDIDOS", "ADMIN"},
    (ESTADO["EN_PREPARACION"], ESTADO["EN_CAMINO"]):      {"PEDIDOS", "ADMIN"},
    (ESTADO["EN_PREPARACION"], ESTADO["CANCELADO"]):      {"ADMIN"},
    (ESTADO["EN_CAMINO"],      ESTADO["ENTREGADO"]):      {"PEDIDOS", "ADMIN"},
}

ESTADOS_CON_STOCK_DECREMENTADO = {
    ESTADO["CONFIRMADO"],
    ESTADO["EN_PREPARACION"],
    ESTADO["EN_CAMINO"],
}

class PedidoService:

    def __init__(
        self,
        uow: PedidoUnitOfWork,
        producto_service: ProductoService,
    ) -> None:
        self._uow = uow
        self._producto_service = producto_service

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _validar_y_construir_detalles(self, items: list, uow: PedidoUnitOfWork) -> list[dict]:
        detalles_data = []

        for item in items:
            producto_locked = uow.productos.get_with_lock(item.producto_id)

            if not producto_locked.disponible:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El producto '{producto_locked.nombre}' no está disponible."
                )
            
            if producto_locked.stock < item.cantidad:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente para '{producto_locked.nombre}'. "
                    f"Disponible: {producto_locked.stock}, solicitado: {item.cantidad}."
                )
            
            precio_snapshot: Decimal = producto_locked.precio
            subtotal = precio_snapshot * item.cantidad

            detalles_data.append({
              "producto_id":      producto_locked.id,
              "producto_nombre":  producto_locked.nombre,
              "cantidad":         item.cantidad,
              "precio_snapshot":  precio_snapshot,
              "subtotal":         subtotal,
              "personalizacion":  item.personalizacion,
            })

        return detalles_data


    def _validar_y_capturar_direccion(self, direccion_id: int, usuario_id: int, uow: PedidoUnitOfWork) -> DireccionPublic:
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

        return DireccionPublic(
            alias=direccion.alias,
            ciudad=direccion.ciudad,
            linea1=direccion.linea1,
            linea2=direccion.linea2,
            provincia=direccion.provincia,
            codigo_postal=direccion.codigo_postal,
            latitud=direccion.latitud,
            longitud=direccion.longitud,
        ).model_dump()


    def _calcular_costo_envio(subtotal: Decimal) -> Decimal:
        UMBRAL_ENVIO_GRATIS = Decimal("10000")
        COSTO_ENVIO_FIJO    = Decimal("500")
        return Decimal("0") if subtotal >= UMBRAL_ENVIO_GRATIS else COSTO_ENVIO_FIJO


    #──────────────────────────────────────────────────────

    def crear_pedido(self, usuario_id: int, data: PedidoCreate) -> PedidoDetail:
        with PedidoUnitOfWork() as uow:
            detalles_data = self._validar_y_construir_detalles(data.items, uow)

            direccion_snapshot = self._validar_y_capturar_direccion(data.direccion_id, usuario_id, uow)

            subtotal = sum(i["subtotal"] for i in detalles_data)
            costo_envio = self._calcular_costo_envio(subtotal)
            total = subtotal + costo_envio

            pedido = uow.pedidos.add(Pedido(
                usuario_id=usuario_id,
                estado_id=ESTADO["PENDIENTE"],           
                direccion_id=data.direccion_id,
                forma_pago_id=data.forma_pago_id,
                direccion_snapshot=direccion_snapshot,   
                costo_envio=costo_envio,
                total=total,                             
            ))

            uow.detalles.add_all([DetallePedido(pedido_id=pedido.id, **item) for item in detalles_data])

            uow.historial.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_anterior_id=None,
                    estado_nuevo_id=ESTADO["PENDIENTE"],
                    usuario_id=usuario_id,
                    observacion="Pedido creado",
                )
            )

            return self._to_pedido_detail(pedido)