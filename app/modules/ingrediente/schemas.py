from typing import List, Optional
from sqlmodel import Field, SQLModel

class IngredienteBase(SQLModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: Optional[str] = Field(default=None)
    es_alergeno: bool = Field(default=False)
    stock_cantidad: int = Field(default=0, ge=0)
    unidad_medida_id: int= Field(gt=0)   
    precio_base: float  = Field(ge=0)


class IngredienteCreate(IngredienteBase):
    pass


class IngredientePublic(IngredienteBase):
    id: int
    activo: bool


class IngredienteUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    es_alergeno: Optional[bool] = None
    stock_cantidad: Optional[int]  = Field(default=None, ge=0)
    unidad_medida_id: int= Field(gt=0)   
    precio_base: float  = Field(ge=0)


class IngredienteList(SQLModel):
    data: List[IngredientePublic]
    total: int