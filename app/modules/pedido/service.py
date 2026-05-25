from decimal import Decimal

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.direcciones.model import DireccionEntrega
from app.modules.direcciones.schemas import DireccionPublic
from app.modules.direcciones.service import DireccionService
from app.modules.pedido.models import DetallePedido, Pedido
from app.modules.pedido.schemas import DetallePedidoCreate, ItemPedidoRequest, PedidoCreate, PedidoDetail, PedidoRead
from app.modules.pedido.unit_of_work import PedidoUnitOfWork
from app.modules.producto.models import Producto
from app.modules.producto.service import ProductoService

ESTADO = {
    "PENDIENTE": 1,
    "CONFIRMADO": 2,
    "EN_PREPARACION": 3,
    "EN_CAMINO": 4,
    "ENTREGADO": 5,
    "CANCELADO": 6,
}

TRANSICIONES_VALIDAS: dict[int, set[int]] = {
    ESTADO["PENDIENTE"]:      {ESTADO["CONFIRMADO"], ESTADO["CANCELADO"]},
    ESTADO["CONFIRMADO"]:     {ESTADO["EN_PREPARACION"], ESTADO["CANCELADO"]},
    ESTADO["EN_PREPARACION"]: {ESTADO["EN_CAMINO"], ESTADO["CANCELADO"]},
    ESTADO["EN_CAMINO"]:      {ESTADO["ENTREGADO"]},
    ESTADO["ENTREGADO"]:      set(),
    ESTADO["CANCELADO"]:      set(),
}

PERMISOS_TRANSICION: dict[tuple[int, int], set[str] | None] = {
    (ESTADO["PENDIENTE"],      ESTADO["CONFIRMADO"]):     None,  # solo sistema vía webhook
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
        resultado = []

        for item in items:
            producto = self._producto_service.obtener_disponible(item.producto_id)

            producto_locked = uow.productos.get_with_lock(item.producto_id)

            if producto_locked.stock_cantidad < item.cantidad:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Stock insuficiente para '{producto.nombre}': "
                        f"disponible={producto_locked.stock_cantidad}, "
                        f"solicitado={item.cantidad}"
                    ),
                )

            resultado.append({
                "producto_id":      producto.id,
                "producto_nombre":  producto.nombre,
                "precio_snapshot":  producto.precio,     
                "cantidad":         item.cantidad,
                "personalizacion":  item.personalizacion,
                "subtotal":         producto.precio * item.cantidad,
            })

        return resultado


    def _validar_y_capturar_direccion(self, direccion_id: int, usuario_id: int, uow: PedidoUnitOfWork) -> dict:
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


    def _calcular_costo_envio(self, direccion_snapshot: dict) -> Decimal:
        return Decimal("500.00")


    def crear_pedido(self, usuario_id: int, data: PedidoCreate) -> PedidoDetail:
        with self._uow:
            items_data = self._validar_y_construir_detalles(data.items, self._uow)

            direccion_snapshot = self._validar_y_capturar_direccion(data.direccion_id, usuario_id, self._uow)

            costo_envio = self._calcular_costo_envio(direccion_snapshot)
            total = sum(i["subtotal"] for i in items_data) + costo_envio

            pedido = Pedido(
                usuario_id=usuario_id,
                estado_id=ESTADO["PENDIENTE"],           
                direccion_id=data.direccion_id,
                forma_pago_id=data.forma_pago_id,
                direccion_snapshot=direccion_snapshot,   
                costo_envio=costo_envio,
                total=total,                             
            )

            self._uow.pedidos.add(pedido)
            self._uow.flush()

            self._uow.detalles.add_all([DetallePedido(pedido_id=pedido.id, **item) for item in items_data])

            self._uow.historial.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_anterior_id=None,
                    estado_nuevo_id=ESTADO["PENDIENTE"],
                    usuario_id=usuario_id,
                    observacion="Pedido creado",
                )
            )

            self._uow.commit() 

        return self._to_pedido_detail(pedido)