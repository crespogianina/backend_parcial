from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_role
from app.modules.usuarios.schemas import UserPublic
from app.modules.usuarios.service import UsuarioService

router = APIRouter()


def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(session)


@router.get("/admin/usuarios", response_model=list[UserPublic])
def list_users(
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    rol: Annotated[Optional[str], Query(description="Filtrar por rol: ADMIN, STOCK, PEDIDOS, CLIENT")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    svc: UsuarioService = Depends(get_usuario_service),
) -> list[UserPublic]:
    return svc.list_all(rol=rol, offset=offset, limit=limit)


@router.post("/admin/usuarios/{user_id}/desactivar", response_model=UserPublic)
def deactivate_user(
    user_id: int,
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    svc: UsuarioService = Depends(get_usuario_service),
) -> UserPublic:
    return svc.set_disabled(user_id, disabled=True)


@router.post("/admin/usuarios/{user_id}/activar", response_model=UserPublic)
def activate_user(
    user_id: int,
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    svc: UsuarioService = Depends(get_usuario_service),
) -> UserPublic:
    return svc.set_disabled(user_id, disabled=False)