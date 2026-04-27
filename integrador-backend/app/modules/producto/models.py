
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlmodel import ARRAY, Column, Numeric, Relationship, SQLModel, Field, String

if TYPE_CHECKING:
    from app.modules.categoria.models import Categoria
    from app.modules.ingrediente.models import Ingrediente
    
class ProductoCategoria(SQLModel, table=True):
    __tablename__ = "producto_categoria"

    producto_id: int= Field(foreign_key="productos.id",primary_key=True)
    categoria_id: int= Field(foreign_key="categorias.id",primary_key=True)
    es_principal: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
    producto: Optional["Producto"] = Relationship(back_populates="producto_categorias")
    categoria: Optional["Categoria"] = Relationship(back_populates="producto_categorias")

class ProductoIngrediente(SQLModel, table=True):
    __tablename__ = "producto_ingrediente"

    producto_id: int= Field(foreign_key="productos.id",primary_key=True)
    ingrediente_id: int= Field(foreign_key="ingredientes.id",primary_key=True)
    es_removible: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
    producto: Optional["Producto"] = Relationship(back_populates="producto_ingredientes")
    ingrediente: Optional["Ingrediente"] = Relationship(back_populates="producto_ingredientes")

class Producto(SQLModel, table=True):
    __tablename__ = "productos"

    id: Optional[int] = Field(default=None, primary_key=True)

    nombre: str = Field(min_length=2, max_length=150, index=True, nullable=False)
    descripcion: Optional[str] = Field(default=None)
    precio_base: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    imagenes_url: Optional[list[str]] = Field(
        sa_column=Column(ARRAY(String))
    )
    stock_cantidad: int = Field(default=0, ge=0,nullable=False)
    disponible: bool = Field(default=True, nullable=False,index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    deleted_at: Optional[datetime] = Field(default=None)

    producto_categorias: List["ProductoCategoria"] = Relationship(
        back_populates="producto"
    )
    producto_ingredientes: List["ProductoIngrediente"] = Relationship(
        back_populates="producto"
    )