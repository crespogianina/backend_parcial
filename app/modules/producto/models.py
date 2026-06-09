
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlmodel import ARRAY, Column, Numeric, Relationship, SQLModel, Field, String


if TYPE_CHECKING:
    from app.modules.pedido.models import DetallePedido
    from app.modules.categoria.models import Categoria
    from app.modules.ingrediente.models import Ingrediente
    
class ProductoCategoria(SQLModel, table=True):
    __tablename__ = "producto_categoria"

    producto_id: int= Field(foreign_key="productos.id",primary_key=True)
    categoria_id: int= Field(foreign_key="categorias.id",primary_key=True)

    es_principal: bool = Field(default=False, nullable=False)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
    
    producto: Optional["Producto"] = Relationship(back_populates="producto_categorias")
    categoria: Optional["Categoria"] = Relationship(back_populates="producto_categorias")


class ProductoIngrediente(SQLModel, table=True):
    __tablename__ = "producto_ingrediente"

    unidad_medida_id: int = Field(foreign_key="unidad_medida.id", nullable=False)

    producto_id: int= Field(foreign_key="productos.id",primary_key=True)
    ingrediente_id: int= Field(foreign_key="ingredientes.id",primary_key=True)

    es_removible: bool = Field(default=False, nullable=False)
    cantidad: Decimal = Field(sa_column=Column(Numeric(10, 3), nullable=False))

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
    
    producto: Optional["Producto"] = Relationship(back_populates="producto_ingredientes")
    ingrediente: Optional["Ingrediente"] = Relationship(back_populates="producto_ingredientes")
    unidad_medida: "UnidadMedida" = Relationship(back_populates="producto_ingredientes")


class Producto(SQLModel, table=True):
    __tablename__ = "productos"

    id: Optional[int] = Field(default=None, primary_key=True)

    unidad_medida_id: Optional[int] = Field(default=None, foreign_key="unidad_medida.id")

    nombre: str = Field(min_length=2, max_length=150, index=True, nullable=False)
    descripcion: Optional[str] = Field(default=None)
    precio_base: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    imagenes_url: Optional[list[str]] = Field(
        sa_column=Column(ARRAY(String))
    )
    stock_cantidad: int = Field(default=0, ge=0,nullable=False)
    disponible: bool = Field(default=True, nullable=False,index=True)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at: Optional[datetime] = Field(default=None)

    producto_categorias: List["ProductoCategoria"] = Relationship(
        back_populates="producto"
    )
    producto_ingredientes: List["ProductoIngrediente"] = Relationship(
        back_populates="producto"
    )
    detalles_pedido: List["DetallePedido"] = Relationship(
    back_populates="producto",
    sa_relationship_kwargs={
        "foreign_keys": "[DetallePedido.producto_id]",
        "lazy": "selectin"
    })
    unidad_medida: Optional["UnidadMedida"] = Relationship(back_populates="productos")



class UnidadMedida(SQLModel, table=True):
    __tablename__ = "unidad_medida"

    id: Optional[int] = Field(default=None, primary_key=True)

    nombre: str = Field(min_length=1, max_length=50, index=True, unique=True, nullable=False)
    simbolo: str = Field(min_length=1, max_length=10, index=True, unique=True, nullable=False)
    tipo: str = Field(min_length=1, max_length=20, index=True, nullable=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
    deleted_at: Optional[datetime] = Field(default=None)

    productos: List["Producto"] = Relationship(back_populates="unidad_medida")
    ingredientes: List["Ingrediente"] = Relationship(back_populates="unidad_medida")
    productos_ingredientes: List[ProductoIngrediente] =  Relationship(back_populates="unidad_medida")