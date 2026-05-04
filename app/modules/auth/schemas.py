from pydantic import BaseModel
from app.modules.usuario.schemas import UsuarioPublic


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UsuarioPublic


class LoginData(BaseModel):
    email: str
    password: str