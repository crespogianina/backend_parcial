from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class ItemPedidoRequest(BaseModel):
    producto_id: int
    cantidad: int = Field(ge=1)
    personalizacion: list[int] = Field(default_factory=list)


class DireccionSnapshot(BaseModel):
    calle: str
    numero: str
    piso: str | None = None
    departamento: str | None = None
    ciudad: str
    referencia: str | None = None
    codigo_postal: str


class UsuarioResumen(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str


class DireccionResumen(BaseModel):
    id: int
    calle: str
    numero: str
    ciudad: str


class EstadoResumen(BaseModel):
    id: int
    nombre: str


class FormaPagoResumen(BaseModel):
    id: int
    nombre: str


class PedidoCreate(BaseModel):
    items: list[ItemPedidoRequest] = Field(min_length=1)
    direccion_id: int
    forma_pago_id: int


class AvanzarEstadoRequest(BaseModel):
    nuevo_estado_id: int
    observacion: str | None = None


class PagoRead(BaseModel):
    id: int
    monto: Decimal
    mp_payment_id: str
    mp_status: str
    creado_en: datetime


class DetallePedidoCreate(BaseModel):
    producto_id: int
    producto_nombre: str
    cantidad: int
    precio_snapshot: Decimal
    subtotal: Decimal
    personalizacion: list[int]


class HistorialEstadoRead(BaseModel):
    id: int
    estado_anterior: EstadoResumen | None  
    estado_nuevo: EstadoResumen
    usuario_id: int | None                 
    observacion: str | None
    creado_en: datetime


class PedidoRead(BaseModel):
    id: int
    estado: EstadoResumen
    total: Decimal
    costo_envio: Decimal
    forma_pago: FormaPagoResumen
    usuario: UsuarioResumen
    direccion: DireccionResumen
    creado_en: datetime
    actualizado_en: datetime

class DetallePedidoRead(BaseModel):
    producto_id: int
    producto_nombre: str
    cantidad: int
    precio_snapshot: Decimal
    subtotal: Decimal
    personalizacion: list[int]

class PedidoDetail(PedidoRead):
    direccion_snapshot: DireccionSnapshot
    detalles: list[DetallePedidoRead]
    historial_estados: list[HistorialEstadoRead]
    pagos: list[PagoRead]

class PedidoListResponse(BaseModel):
    items: list[PedidoRead]
    total: int
    offset: int
    limit: int