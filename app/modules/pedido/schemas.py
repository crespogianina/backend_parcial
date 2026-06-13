from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import Field, model_validator
from sqlmodel import SQLModel

class ItemPedidoRequest(SQLModel):
    producto_id: int
    cantidad: int = Field(ge=1)
    personalizacion: Optional[list[int]] = Field(default_factory=list)

class CrearPedidoRequest(SQLModel):
    items: list[ItemPedidoRequest] = Field(min_length=1)
    forma_pago_codigo: str
    direccion_id: Optional[int] = None
    notas: Optional[str] = None

class AvanzarEstadoRequest(SQLModel):
    nuevo_estado: str
    motivo: Optional[str] = None
    
    @model_validator(mode="after")
    def _validar(self):
        self.nuevo_estado = self.nuevo_estado.upper().strip()
 
        if self.nuevo_estado == "CANCELADO" and not (self.motivo and self.motivo.strip()):
            raise ValueError(
                "El motivo es obligatorio cuando nuevo_estado es CANCELADO (RN-05)."
            )
        return self

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
 
class DireccionSnapshot(SQLModel):
    alias:         Optional[str] = None
    ciudad:        str
    linea1:        str
    linea2:        Optional[str] = None
    provincia:     Optional[str] = None
    codigo_postal: Optional[str] = None

class PagoRead(SQLModel):
    id: int
    monto: Decimal
    mp_payment_id: Optional[int] = None 
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
    estado_desde: Optional[str] = None
    estado_hacia: str
    usuario_id: Optional[int] = None   
    motivo: Optional[str] = None
    created_at: datetime

class PedidoRead(SQLModel):
    id: int
    estado_codigo: str
    subtotal: Decimal
    descuento: Decimal
    costo_envio: Decimal
    total: Decimal
    created_at: datetime
    cantidad_items: Optional[int] = None
    cliente_nombre: Optional[str] = None
    cliente_email: Optional[str] = None

class PedidoDetail(PedidoRead):
    usuario_id: int
    direccion_id: Optional[int] = None
    forma_pago_codigo: str
    notas: Optional[str] = None
    actualizado_en: Optional[datetime] = None
 
    estado: EstadoResumen
    forma_pago: FormaPagoResumen
    usuario: UsuarioResumen
    direccion: Optional[DireccionResumen] = None
    direccion_snapshot: Optional[DireccionSnapshot] = None
 
    detalles: list[DetallePedidoRead]
    historial_estados: list[HistorialEstadoRead]
    pagos: list[PagoRead]

class PaginatedPedidos(SQLModel):
    items: list[PedidoRead]
    total: int