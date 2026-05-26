from typing import Annotated
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from app.core.database import get_session
from app.core.security import decode_access_token
from app.modules.usuarios.model import Usuario
from app.modules.usuarios.schemas import UserPublic
from app.modules.usuarios.service import UsuarioService

def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(session)


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str | None:
        token = request.cookies.get("access_token")

        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No autenticado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        return token


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/usuario/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    svc: Annotated[UsuarioService, Depends(get_usuario_service)]
) -> UserPublic:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    username: str | None = payload.get("sub")

    if username is None:
        raise credentials_exception

    user = svc.get_by_username(username)

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user( current_user: Annotated[Usuario, Depends(get_current_user)]) -> UserPublic:
    if current_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario desactivada",
        )

    return UserPublic.model_validate(current_user)


def require_role(allowed_roles: list[str]):
    async def role_checker( current_user: Annotated[Usuario, Depends(get_current_active_user)]) -> UserPublic:
        if not any(role in allowed_roles for role in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permisos insuficientes. Tus roles son '{current_user.roles}'. "
                    f"Se requiere uno de: {allowed_roles}"
                ),
            )

        return UserPublic.model_validate(current_user)

    return role_checker