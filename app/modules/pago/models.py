from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Numeric
from sqlmodel import Column, Field, Relationship, SQLModel

from app.modules.pedido.models import Pedido


class Pago(SQLModel, table=True):
    __tablename__ = "pagos"

    id: Optional[int] = Field(default=None, primary_key=True)

    pedido_id: int = Field(sa_column=Column(BigInteger, ForeignKey("pedidos.id"), nullable=False))
 
    mp_payment_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, unique=True, nullable=True))
    mp_status: str = Field(max_length=30, nullable=False)
    mp_status_detail: Optional[str] = Field(default=None, max_length=100)
    external_reference: str = Field(max_length=100, nullable=False, unique=True)
    idempotency_key: str = Field(max_length=100, nullable=False, unique=True)
    transaction_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    payment_method_id: Optional[str] = Field(default=None, max_length=50)
 
    mp_preference_id: Optional[str] = Field(default=None, max_length=100)
    mp_init_point: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    
    #pedido: Pedido = Relationship(back_populates="pagos")