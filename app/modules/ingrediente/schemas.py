from typing import List, Optional

from sqlmodel import Field, SQLModel

class IngredienteBase(SQLModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: Optional[str] = Field(default=None)
    es_alergeno: bool = Field(default=False)

class IngredienteCreate(IngredienteBase):
    pass

class IngredientePublic(IngredienteBase):
    id: int

class IngredienteUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    es_alergeno: Optional[bool] = None

class IngredienteList(SQLModel):
    data: List[IngredientePublic]
    total: int
