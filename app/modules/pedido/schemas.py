from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field
from sqlmodel import SQLModel


class ItemPedidoRequest(SQLModel):
    producto_id: int
    cantidad: int = Field(ge=1)
    personalizacion: Optional[list[int]] = Field(default_factory=list)


class DireccionSnapshot(SQLModel):
    alias:          Optional[str] = None
    ciudad:         str
    linea1:         str
    linea2:         Optional[str] = None
    provincia:      str
    codigo_postal:  Optional[str] = None
    latitud:        Optional[float] = None
    longitud:       Optional[float] = None


class UsuarioResumen(SQLModel):
    id: int
    nombre: str
    apellido: str
    email: str


class DireccionResumen(SQLModel):
    id: int
    linea1: str          
    ciudad: str


class EstadoResumen(SQLModel):
    codigo: str          
    descripcion: str    


class FormaPagoResumen(SQLModel):
    codigo: str          
    descripcion: str    


class PedidoCreate(SQLModel):
    items: list[ItemPedidoRequest] = Field(min_length=1)
    direccion_id: int
    forma_pago_codigo: str


class AvanzarEstadoRequest(SQLModel):
    nuevo_estado: str
    observacion: str | None = None


class PagoRead(SQLModel):
    id: int
    monto: Decimal
    mp_payment_id: str
    mp_status: str
    creado_en: datetime


class DetallePedidoCreate(SQLModel):
    producto_id: int
    producto_nombre: str
    cantidad: int
    precio_snapshot: Decimal
    subtotal: Decimal
    personalizacion: Optional[list[int]] = Field(default_factory=list)


class DetallePedidoRead(SQLModel):
    producto_id: int
    nombre_snapshot: str   
    cantidad: int
    precio_snapshot: Decimal
    subtotal_snap: Decimal  
    personalizacion: Optional[list[int]] = None


class HistorialEstadoRead(SQLModel):
    id: int
    estado_desde: str
    estado_hacia: Optional[str] = None
    usuario_id: int
    motivo: Optional[str] = None
    created_at: datetime


class PedidoRead(SQLModel):
    id: int
    usuario_id: int
    direccion_id: Optional[int] = None
    estado_codigo: str
    forma_pago_codigo: str
    subtotal: Decimal
    descuento: Decimal
    costo_envio: Decimal
    total: Decimal
    notas: Optional[str] = None
    creado_en: datetime = Field(alias="created_at")      
    actualizado_en: datetime = Field(alias="updated_at")
    estado: EstadoResumen
    forma_pago: FormaPagoResumen
    usuario: UsuarioResumen
    direccion: Optional[DireccionResumen] = None


class PedidoDetail(PedidoRead):
    direccion_snapshot: Optional[DireccionSnapshot] = None
    detalles: list[DetallePedidoRead]
    historial_estados: list[HistorialEstadoRead]
    pagos: list[PagoRead]


class PedidoListResponse(SQLModel):
    items: list[PedidoRead]
    total: int