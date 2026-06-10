from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Response, status
from fastapi.params import Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from app.core.database import get_session
from app.core.deps import get_current_active_user, require_role
from app.modules.usuarios.schemas import UserCreate, UserPublic
from app.modules.usuarios.service import UsuarioService

router = APIRouter()


def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(session)


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, svc: UsuarioService = Depends(get_usuario_service)) -> UserPublic:
    return svc.register(user_in)


@router.post("/token")
def login( 
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response, svc: UsuarioService = Depends(get_usuario_service)
) -> dict:
    token = svc.authenticate(form_data.username, form_data.password)

    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        max_age=1800,
        samesite="lax",
        secure=False,
    )

    return {
        "mensaje": "Login exitoso. Sesión iniciada.",
        "access_token": token.access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(key="access_token", httponly=True, samesite="lax", secure=False)
    return {"mensaje": "Sesión cerrada exitosamente"}


@router.get("/me", response_model=UserPublic)
def read_me(current_user: Annotated[UserPublic, Depends(get_current_active_user)]) -> UserPublic:
    return current_user


@router.get("/privado")
def ruta_privada(current_user: Annotated[UserPublic, Depends(get_current_active_user)]) -> dict:
    return {
        "mensaje": f"¡Hola, {current_user.nombre}! Accediste a una ruta privada.",
        "tus_roles": current_user.roles,
    }


@router.get("/admin/usuarios", response_model=list[UserPublic])
def list_users(
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    rol: Annotated[Optional[str], Query(description="Filtrar por rol: ADMIN, STOCK, PEDIDOS, CLIENT")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    svc: UsuarioService = Depends(get_usuario_service)
) -> list[UserPublic]:
    return svc.list_all(rol=rol, offset=offset, limit=limit)


@router.post("/admin/usuarios/{user_id}/desactivar", response_model=UserPublic)
def deactivate_user( user_id: int, _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))], svc: UsuarioService = Depends(get_usuario_service)) -> UserPublic:
    return svc.set_disabled(user_id, disabled=True)


@router.post("/admin/usuarios/{user_id}/activar", response_model=UserPublic)
def activate_user( user_id: int, _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))], svc: UsuarioService = Depends(get_usuario_service)) -> UserPublic:
    return svc.set_disabled(user_id, disabled=False)