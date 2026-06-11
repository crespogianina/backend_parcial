from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.core.rate_limit import check_auth_rate_limit, record_auth_failure
from app.modules.usuarios.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse
from app.modules.usuarios.service import UsuarioService

router = APIRouter()


def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(session)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_in: RegisterRequest,
    svc: UsuarioService = Depends(get_usuario_service),
) -> UserResponse:
    return svc.register(user_in)


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    user_in: LoginRequest,
    svc: UsuarioService = Depends(get_usuario_service),
) -> TokenResponse:
    check_auth_rate_limit(request)
    try:
        return svc.login(user_in)
    except HTTPException as exc:
        if exc.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
        ):
            record_auth_failure(request)
        raise


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    refresh_in: RefreshRequest,
    svc: UsuarioService = Depends(get_usuario_service),
) -> TokenResponse:
    return svc.refresh(refresh_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    refresh_in: RefreshRequest,
    svc: UsuarioService = Depends(get_usuario_service),
) -> Response:
    svc.logout(current_user.id, refresh_in.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def read_me(
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
    svc: UsuarioService = Depends(get_usuario_service),
) -> UserResponse:
    return svc.get_me(current_user.id)