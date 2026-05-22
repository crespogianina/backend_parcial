from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from sqlmodel import SQLModel, Field


class UserCreate(SQLModel):
    nombre: str = Field(max_length=80)
    apellido: str = Field(max_length=80)
    username: str = Field(max_length=80)
    email: EmailStr
    celular: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(min_length=8)


class UserPublic(SQLModel):
    id: int
    nombre: str
    apellido: str
    username: str
    email: str
    celular: Optional[str] = None
    deleted_at: Optional[datetime] = None

    roles: list[str] = []


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(SQLModel):
    sub: str     
    roles: list[str]  
    exp: int          