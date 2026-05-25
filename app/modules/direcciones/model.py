
from datetime import datetime, timezone
from typing import TYPE_CHECKING, TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Index, Numeric
from sqlmodel import Column, ForeignKey, Relationship, SQLModel, Field
from app.modules.pedido.models import Pedido

if TYPE_CHECKING:
    from app.modules.usuarios.model import Usuario


class DireccionEntrega(SQLModel, table=True):
    __tablename__ = "direcciones_entrega"

    __table_args__ = (Index("ix_direcciones_entrega_usuario_id", "usuario_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)

    usuario_id: int = Field(sa_column=Column(BigInteger, ForeignKey("usuarios.id"), nullable=False))

    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: str = Field(nullable=False)
    linea2: Optional[str] = Field(default=None)
    ciudad: str = Field(nullable=False, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)

    latitud: Optional[float] = Field(default=None, sa_column=Column(Numeric(9, 6)))
    longitud: Optional[float] = Field(default=None, sa_column=Column(Numeric(9, 6)))

    es_principal: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at: Optional[datetime] = Field(default=None)

    usuario: Optional["Usuario"] = Relationship(back_populates="direcciones")
    pedidos: Optional[list["Pedido"]] = Relationship(
        back_populates="direccion",
        sa_relationship_kwargs={"foreign_keys": "[Pedido.direccion_id]", "lazy": "selectin"}
    )
