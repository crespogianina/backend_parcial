# from typing import Annotated

# from fastapi import APIRouter, Depends, status, Response
# from fastapi.security import OAuth2PasswordRequestForm
# from sqlmodel import Session

# from app.core.database import get_session
# from app.core.deps import get_current_active_user, require_role
# from app.modules.usuarios.model import Usuario, UserCreate, UserPublic, Token
# from app.modules.usuarios.service import UsuarioService

# router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
#     return UsuarioService(session)


# # ─── Registro ─────────────────────────────────────────────────────────────────

# @router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
# def register( user_in: UserCreate, svc: UsuarioService = Depends(get_usuario_service)):
#     return svc.register(user_in)


# # ─── Login (OAuth2 Password Flow) ────────────────────────────────────────────

# @router.post("/token")
# def login( form_data: Annotated[OAuth2PasswordRequestForm, Depends()], response: Response, svc: UsuarioService = Depends(get_usuario_service) ):
#     token = svc.authenticate(form_data.username, form_data.password)
    
#     response.set_cookie(
#         key="access_token",
#         value=token.access_token,
#         httponly=True,
#         max_age=1800,  
#         samesite="lax",
#         secure=False,  
#     )

#     return {"mensaje": "Login exitoso. Sesión iniciada."}

# @router.post("/logout")
# def logout(response: Response):
#     response.delete_cookie( key="access_token", httponly=True, samesite="lax", secure=False)

#     return {"mensaje": "Sesión cerrada exitosamente"}


# # ─── Rutas protegidas ────────────────────────────────────────────────────────

# @router.get("/me", response_model=UserPublic)
# def read_me(current_user: Annotated[Usuario, Depends(get_current_active_user)]):
#     return current_user


# @router.get("/privado")
# def ruta_privada(current_user: Annotated[Usuario, Depends(get_current_active_user)],):
#     return {
#         "mensaje": f"¡Hola, {current_user.full_name}! Accediste a una ruta privada.",
#         "tu_rol": current_user.role,
#     }


# # ─── Rutas de administración (RBAC) ──────────────────────────────────────────

# @router.get("/admin/usuarios", response_model=list[UserPublic])
# def list_users(_admin: Annotated[Usuario, Depends(require_role(["admin"]))], svc: UsuarioService = Depends(get_usuario_service)):
#     return svc.list_all()


# @router.post("/admin/usuarios/{user_id}/desactivar", response_model=UserPublic)
# def deactivate_user( user_id: int, _admin: Annotated[Usuario, Depends(require_role(["admin"]))], svc: UsuarioService = Depends(get_usuario_service)):
#     return svc.set_disabled(user_id, disabled=True)


# @router.post("/admin/usuarios/{user_id}/activar", response_model=UserPublic)
# def activate_user( user_id: int, _admin: Annotated[Usuario, Depends(require_role(["admin"]))], svc: UsuarioService = Depends(get_usuario_service)):
#     return svc.set_disabled(user_id, disabled=False)

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user, require_role
from app.modules.usuarios.model import Usuario
from app.modules.usuarios.schemas import UserCreate, UserPublic
from app.modules.usuarios.service import UsuarioService

router = APIRouter()


def get_usuario_service( session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(session)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post( "/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register( user_in: UserCreate, svc: UsuarioService = Depends(get_usuario_service)):
    return svc.register(user_in)


@router.post("/token")
def login( form_data: Annotated[OAuth2PasswordRequestForm, Depends()], response: Response, svc: UsuarioService = Depends(get_usuario_service)):
    token = svc.authenticate( form_data.username, form_data.password )

    response.set_cookie( key="access_token", value=token.access_token, httponly=True, max_age=1800, samesite="lax", secure=False )

    return {
        "mensaje": "Login exitoso. Sesión iniciada.",
        "access_token": token.access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie( key="access_token", httponly=True, samesite="lax", secure=False )

    return {"mensaje": "Sesión cerrada exitosamente"}


@router.get("/me", response_model=UserPublic)
def read_me( current_user: Annotated[UserPublic , Depends(get_current_active_user)] ):
    return current_user


@router.get("/privado")
def ruta_privada( current_user: Annotated[UserPublic , Depends(get_current_active_user)]):
    return {
        "mensaje": f"¡Hola, {current_user.full_name}! Accediste a una ruta privada.",
        "tu_rol": current_user.role,
    }


@router.get("/admin/usuarios", response_model=list[UserPublic])
def list_users( _admin: Annotated[UserPublic, Depends(require_role(["admin"]))], svc: UsuarioService = Depends(get_usuario_service)):
    return svc.list_all()


@router.post( "/admin/usuarios/{user_id}/desactivar", response_model=UserPublic )
def deactivate_user( user_id: int, _admin: Annotated[UserPublic, Depends(require_role(["admin"]))], svc: UsuarioService = Depends(get_usuario_service) ):
    return svc.set_disabled(user_id, disabled=True)


@router.post( "/admin/usuarios/{user_id}/activar", response_model=UserPublic )
def activate_user( user_id: int, _admin: Annotated[UserPublic, Depends(require_role(["admin"]))], svc: UsuarioService = Depends(get_usuario_service) ):
    return svc.set_disabled(user_id, disabled=False)