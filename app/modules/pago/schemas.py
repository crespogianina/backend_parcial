from typing import Optional
from sqlmodel import SQLModel, Field


class CrearPagoRequest(SQLModel):
    pedido_id: int = Field(..., description="ID del pedido a pagar")


class ConfirmarPagoRequest(SQLModel):
    pedido_id:  int = Field(..., description="ID del pedido")
    payment_id: Optional[int] = Field(default=None, description="ID del pago en MP")


class PagoCrearResponse(SQLModel):
    pago_id:       int
    preference_id: str
    init_point:    Optional[str] = None
    public_key:    Optional[str] = None


class PagoEstadoResponse(SQLModel):
    estado:     Optional[str] = None
    pedido_id:  int
