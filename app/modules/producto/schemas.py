from decimal import Decimal
from typing import List, Optional

from sqlmodel import ARRAY, Column, Field, SQLModel, String

class CategoriaAsignar(SQLModel):
    categoria_id: int
    es_principal: bool = False

class IngredienteAsignar(SQLModel):
    ingrediente_id: int
    es_removible: bool = False

class ProductoBase(SQLModel):
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: Optional[str] = Field(default=None)
    precio_base: float  = Field(ge=0)
    imagenes_url: Optional[list[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    stock_cantidad: int = Field(default=0, ge=0)
    disponible: bool = Field(default=True)

class ProductoCreate(ProductoBase):
    categorias: List[CategoriaAsignar] = Field(min_length=1)  
    ingredientes: Optional[List[IngredienteAsignar]] = Field(default_factory=list)

class ProductoPublic(ProductoBase):
    id: int

class ProductoUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio_base: Optional[float] = Field(default=None, ge=0)
    imagenes_url: Optional[list[str]] = None
    stock_cantidad: Optional[int] = Field(default=None, ge=0)
    disponible: Optional[bool] = None
    categorias: Optional[List[CategoriaAsignar]] = None  
    ingredientes: Optional[List[IngredienteAsignar]] = None

class ProductoList(SQLModel):
    data: List[ProductoPublic]
    total: int