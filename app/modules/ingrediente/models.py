
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Column, Numeric
from sqlmodel import Relationship, SQLModel, Field
from app.modules.producto.models import ProductoIngrediente, UnidadMedida


class Ingrediente(SQLModel, table=True):
    __tablename__ = "ingredientes"

    id: Optional[int] = Field(default=None, primary_key=True)

    unidad_medida_id: int = Field(foreign_key="unidad_medida.id", nullable=False)

    nombre: str = Field(min_length=2, max_length=100, index=True,nullable=False, unique=True)
    descripcion: Optional[str] = Field(default=None)
    es_alergeno: bool = Field(default=False, nullable=False)
    stock_cantidad: int= Field(default=0, ge=0, nullable=False)
    precio_base: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at: Optional[datetime] = Field(default=None)

    producto_ingredientes: List["ProductoIngrediente"] = Relationship(
        back_populates="ingrediente"
    )
    unidad_medida: UnidadMedida = Relationship(back_populates="ingredientes")