from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.params import Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from app.core.database import get_session
from app.core.deps import get_current_active_user, require_role
from app.core.rate_limit import check_auth_rate_limit, record_auth_failure
from app.modules.usuarios.schemas import UserCreate, UserPublic
from app.modules.usuarios.service import UsuarioService

router = APIRouter()


def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(session)


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(
    request: Request,
    user_in: UserCreate,
    svc: UsuarioService = Depends(get_usuario_service),
) -> UserPublic:
    check_auth_rate_limit(request)
    try:
        return svc.register(user_in)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_409_CONFLICT:
            record_auth_failure(request)
        raise


@router.post("/token")
def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    svc: UsuarioService = Depends(get_usuario_service),
) -> dict:
    check_auth_rate_limit(request)
    try:
        token = svc.authenticate(form_data.username, form_data.password)
    except HTTPException as exc:
        if exc.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
        ):
            record_auth_failure(request)
        raise

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
    nombre: Annotated[Optional[str], Query(description="Filtrar por nombre o apellido")] = None,
    email: Annotated[Optional[str], Query(description="Filtrar por email")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    svc: UsuarioService = Depends(get_usuario_service)
) -> list[UserPublic]:
    return svc.list_all(rol=rol, nombre=nombre, email=email, offset=offset, limit=limit)


@router.post("/admin/usuarios/{user_id}/desactivar", response_model=UserPublic)
def deactivate_user( user_id: int, _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))], svc: UsuarioService = Depends(get_usuario_service)) -> UserPublic:
    return svc.set_disabled(user_id, disabled=True)


@router.post("/admin/usuarios/{user_id}/activar", response_model=UserPublic)
def activate_user( user_id: int, _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))], svc: UsuarioService = Depends(get_usuario_service)) -> UserPublic:
    return svc.set_disabled(user_id, disabled=False)