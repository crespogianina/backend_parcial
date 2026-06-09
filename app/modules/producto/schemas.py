from decimal import Decimal
from typing import List, Optional
from sqlmodel import Field, SQLModel

class CategoriaAsignar(SQLModel):
    categoria_id: int
    es_principal: bool = False


class IngredienteAsignar(SQLModel):
    ingrediente_id: int
    es_removible: bool = False
    unidad_medida_id: int 
    cantidad: Decimal = Field(gt=0)

class UnidadMedidaProductoRead(SQLModel):
    id: int
    nombre: str
    simbolo: str

class CategoriaProductoRead(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    es_principal: bool


class IngredienteProductoRead(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    es_removible: bool


class ProductoBase(SQLModel):
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: Optional[str] = Field(default=None)
    precio_base: float  = Field(ge=0)
    imagenes_url: Optional[list[str]] = None
    # stock_cantidad: int = Field(default=0, ge=0)
    disponible: bool = Field(default=True)



class ProductoCreate(ProductoBase):
    categorias: List[CategoriaAsignar] = Field(min_length=1)  
    ingredientes: Optional[List[IngredienteAsignar]] = Field(default_factory=list)
    unidad_medida_id: int= Field(gt=0) 

class ProductoPublic(ProductoBase):
    id: int
    activo: bool
    unidad_medida: Optional[UnidadMedidaProductoRead] = None
    categorias: List[CategoriaProductoRead] = Field(default_factory=list)
    ingredientes: List[IngredienteProductoRead] = Field(default_factory=list)
    stock_cantidad: Optional[int] = Field(default=None, ge=0)


class ProductoUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio_base: Optional[float] = Field(default=None, ge=0)
    imagenes_url: Optional[list[str]] = None
    stock_cantidad: Optional[int] = Field(default=None, ge=0)
    disponible: Optional[bool] = None
    categorias: Optional[List[CategoriaAsignar]] = None  
    ingredientes: Optional[List[IngredienteAsignar]] = None
    unidad_medida_id: Optional[int]= Field(gt=0, default=None) 

class ProductoList(SQLModel):
    data: List[ProductoPublic]
    total: int