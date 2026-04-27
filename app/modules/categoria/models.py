
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Relationship, SQLModel, Field

if TYPE_CHECKING:
    from app.modules.producto.models import ProductoCategoria

class Categoria(SQLModel, table=True):
    __tablename__ = "categorias"

    id: Optional[int] = Field(default=None, primary_key=True)

    parent_id: Optional[int] = Field(default=None, foreign_key="categorias.id", nullable=True, index=True)

    nombre: str = Field(min_length=2, max_length=100, index=True, nullable=False, unique=True)
    descripcion: Optional[str] = Field(default=None)
    imagen_url: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    deleted_at: Optional[datetime] = None

    hijos: List["Categoria"] = Relationship(
        back_populates='padre',
        sa_relationship_kwargs={
        'foreign_keys': '[Categoria.parent_id]',
        'lazy': 'selectin',
        },
    )
    
    padre: Optional["Categoria"] = Relationship(
        back_populates='hijos',
        sa_relationship_kwargs={
        'foreign_keys': '[Categoria.parent_id]',
        'remote_side': '[Categoria.id]',
        },
    )

    producto_categorias: List["ProductoCategoria"] = Relationship(
        back_populates="categoria"
    )
