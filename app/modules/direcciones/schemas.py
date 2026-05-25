from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, SQLModel


class DireccionBase(SQLModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: str = Field(min_length=1)
    linea2: Optional[str] = Field(default=None)
    ciudad: str = Field(min_length=1, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)
    latitud: Optional[float] = Field(default=None)
    longitud: Optional[float] = Field(default=None)


class DireccionCreate(DireccionBase):
    es_principal: Optional[bool] = Field(default=None)


class DireccionUpdate(SQLModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: Optional[str] = Field(default=None, min_length=1)
    linea2: Optional[str] = None
    ciudad: Optional[str] = Field(default=None, min_length=1, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class DireccionPublic(DireccionBase):
    id: int
    usuario_id: int
    es_principal: bool
    activo: bool
    created_at: datetime
    updated_at: datetime


class DireccionList(SQLModel):
    data: List[DireccionPublic]
    total: int
