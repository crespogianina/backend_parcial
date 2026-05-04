from enum import Enum

from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

class RolEnum(str, Enum):
    ADMIN = "ADMIN"
    STOCK = "STOCK"
    PEDIDOS = "PEDIDOS"
    CLIENT = "CLIENT"

class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str
    rol: RolEnum


class UsuarioPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    rol: RolEnum
    # is_active: bool

