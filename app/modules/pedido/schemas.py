from pydantic import Field
from sqlmodel import SQLModel


class PedidoCreate(SQLModel):
    items: list[str]
    direccion_id: str
    forma_pago_id: str


class ItemPedidoRequest(SQLModel):
    producto_id: str
    cantidad: int
    personalizacion: list[int]


class AvanzarEstadoRequest(SQLModel):
    observacion: str


class PedidoRead(SQLModel):
    id: str
    estado: str
    total: str
    costo_envio: str
    creado_en: str
    actualizado_en: str
    usuario: str
    direccion: str


class DetallePedidoRead(SQLModel):
    id: int
    producto_id: int
    producto_nombre: str
    cantidad: int
    precio_unitario: int
    subtotal: int
    personalizacion: int


class PedidoDetail(PedidoRead):
    detalles: list[DetallePedidoRead]
    historial_estados: list[str]
    # pagos: str[Pagps]
    # snapshots