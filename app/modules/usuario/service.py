from fastapi import HTTPException, status
from sqlmodel import Session
from app.modules.usuario.unit_of_work import UsuarioUnitOfWork
from app.modules.usuario.schemas import UsuarioCreate, UsuarioPublic
from app.modules.usuario.models import Usuario
from app.core.passwords import get_password_hash


class UsuarioService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data: UsuarioCreate) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            if uow.usuarios.get_by_email(data.email):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado")
            usuario = Usuario(email=data.email, password_hash=get_password_hash(data.password))
            uow.usuarios.add(usuario)
            return UsuarioPublic.model_validate(usuario)

    def get_by_email(self, email: str) -> Usuario | None:
        with UsuarioUnitOfWork(self._session) as uow:
            return uow.usuarios.get_by_email(email)
