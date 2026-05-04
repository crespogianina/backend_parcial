from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.usuario.schemas import UsuarioCreate, UsuarioPublic
from app.modules.usuario.service import UsuarioService

router = APIRouter()


def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(session)


@router.post("/", response_model=UsuarioPublic, status_code=status.HTTP_201_CREATED, summary="Crear un usuario")
def create_usuario(data: UsuarioCreate, svc: UsuarioService = Depends(get_usuario_service)) -> UsuarioPublic:
    return svc.create(data)
