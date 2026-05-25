from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from sqlmodel import SQLModel


class ItemPedidoRequest(BaseModel):
    producto_id: int
    cantidad: int = Field(ge=1)
    personalizacion: list[int] = Field(default_factory=list)


# ── Single definition of DireccionSnapshot ───────────────────────────────────
class DireccionSnapshot(BaseModel):
    alias:          Optional[str] = None
    ciudad:         str
    linea1:         str
    linea2:         Optional[str] = None
    provincia:      str
    codigo_postal:  Optional[str] = None
    latitud:        Optional[float] = None
    longitud:       Optional[float] = None


# ── Resumen schemas — field names must match the ORM models ──────────────────
class UsuarioResumen(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str

    model_config = {"from_attributes": True}


class DireccionResumen(BaseModel):
    id: int
    linea1: str          # match DireccionEntrega column name
    ciudad: str

    model_config = {"from_attributes": True}


class EstadoResumen(BaseModel):
    codigo: str          # EstadoPedido PK is "codigo", not "id"
    descripcion: str     # EstadoPedido has "descripcion", not "nombre"

    model_config = {"from_attributes": True}


class FormaPagoResumen(BaseModel):
    codigo: str          # FormaPago PK is "codigo", not "id"
    descripcion: str     # FormaPago has "descripcion", not "nombre"

    model_config = {"from_attributes": True}


# ── Request / create schemas ──────────────────────────────────────────────────
class PedidoCreate(BaseModel):
    items: list[ItemPedidoRequest] = Field(min_length=1)
    direccion_id: int
    forma_pago_codigo: str


class AvanzarEstadoRequest(BaseModel):
    nuevo_estado: str
    observacion: str | None = None


# ── Read schemas ──────────────────────────────────────────────────────────────
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


class DetallePedidoRead(BaseModel):
    producto_id: int
    nombre_snapshot: str   # matches DetallePedido.nombre_snapshot
    cantidad: int
    precio_snapshot: Decimal
    subtotal_snap: Decimal  # matches DetallePedido.subtotal_snap
    personalizacion: Optional[list[int]] = None


class HistorialEstadoRead(BaseModel):
    id: int
    estado_desde: str
    estado_hacia: Optional[str] = None
    usuario_id: int
    motivo: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PedidoRead(BaseModel):
    id: int
    usuario_id: int
    direccion_id: Optional[int]
    estado_codigo: str
    forma_pago_codigo: str
    subtotal: Decimal
    descuento: Decimal
    costo_envio: Decimal
    total: Decimal
    notas: Optional[str] = None
    creado_en: datetime
    actualizado_en: datetime
    estado: EstadoResumen
    forma_pago: FormaPagoResumen
    usuario: UsuarioResumen
    direccion: Optional[DireccionResumen]

    model_config = {"from_attributes": True}


class PedidoDetail(PedidoRead):
    direccion_snapshot: Optional[DireccionSnapshot] = None
    detalles: list[DetallePedidoRead]
    historial_estados: list[HistorialEstadoRead]
    pagos: list[PagoRead]


class PedidoListResponse(BaseModel):
    items: list[PedidoRead]
    total: int
    offset: int
    limit: int