from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional


class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str


class UsuarioPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
