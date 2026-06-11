from datetime import datetime

from pydantic import EmailStr, Field
from sqlmodel import SQLModel


class RegisterRequest(SQLModel):
    nombre: str = Field(min_length=2, max_length=80)
    apellido: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(SQLModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(SQLModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(SQLModel):
    id: int
    nombre: str
    apellido: str
    email: EmailStr
    roles: list[str]
    created_at: datetime


class CurrentUser(UserResponse):
    username: str | None = None
    celular: str | None = None
    deleted_at: datetime | None = None


# Compatibilidad temporal con el resto del proyecto mientras se migra la capa auth.
UserCreate = RegisterRequest
UserPublic = CurrentUser
Token = TokenResponse


class TokenPayload(SQLModel):
    sub: str
    roles: list[str]
    exp: int