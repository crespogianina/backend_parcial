from typing import List, Optional

from sqlmodel import Field, SQLModel

class CategoriaBase(SQLModel):
    nombre: str = Field(max_length=100)
    descripcion: Optional[str] = Field(default=None)
    imagen_url: Optional[str] = Field(default=None)
    parent_id: Optional[int] = Field(default=None, ge=1)

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaPublic(CategoriaBase):
    id: int

class CategoriaUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    parent_id: Optional[int] = Field(default=None, ge=1)

class CategoriaConHijosRead(CategoriaPublic):
    hijos: list[CategoriaPublic] = Field(default_factory=list)

class CategoriaList(SQLModel):
    data: List[CategoriaPublic]
    total: int

class CategoriaTreeRead(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    parent_id: Optional[int] = None
    hijos: list["CategoriaTreeRead"] = Field(default_factory=list)