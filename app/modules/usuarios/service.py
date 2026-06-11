from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session
from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_token_con_motivo,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.modules.usuarios.model import Usuario, UsuarioRol
from app.modules.usuarios.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserPublic, UserResponse
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork


class UsuarioService:

    def __init__(self, session: Session):
        self._session = session

    def _usuario_roles(self, usuario: Usuario) -> list[str]:
        return [ur.rol_codigo for ur in usuario.usuario_roles]

    def _to_user_public(self, usuario: Usuario) -> UserPublic:
        return UserPublic(
            id=usuario.id,
            nombre=usuario.nombre,
            apellido=usuario.apellido,
            email=usuario.email,
            roles=self._usuario_roles(usuario),
            created_at=usuario.created_at,
            username=None,
            celular=usuario.celular,
            deleted_at=usuario.deleted_at,
        )

    def _to_user_response(self, usuario: Usuario) -> UserResponse:
        return UserResponse(
            id=usuario.id,
            nombre=usuario.nombre,
            apellido=usuario.apellido,
            email=usuario.email,
            roles=self._usuario_roles(usuario),
            created_at=usuario.created_at,
        )

    # ── Helpers ──────────────────────────────────────────────────────

    def autenticar_websocket(self, token: str) -> tuple[Optional[tuple[int, str]], str]:
        payload, motivo = decode_token_con_motivo(token)

        if payload is None:
            return None, motivo

        email = payload.get("sub")

        if not email:
            return None, "invalido"

        user = self.get_by_email(email)

        if not user or user.deleted_at is not None:
            return None, "usuario_inactivo"

        role = next((r for r in user.roles if r), "CLIENT")
        return (user.id, role), "ok"

    # ────────────────────────────────────────────────────────

    def get_by_email(self, email: str) -> UserPublic | None:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = uow.usuarios.get_by_email(email)

            if usuario is None:
                return None

            return self._to_user_public(usuario)


    def get_by_username(self, username: str) -> UserPublic | None:
        return self.get_by_email(username)


    def register(self, user_in: RegisterRequest) -> UserResponse:
        with UsuarioUnitOfWork(self._session) as uow:
            if uow.usuarios.get_by_email(user_in.email):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El email ya está registrado",
                )

            usuario = Usuario(
                nombre=user_in.nombre,
                apellido=user_in.apellido,
                email=user_in.email,
                password_hash=hash_password(user_in.password),
            )

            result = uow.usuarios.add(usuario)

            rol_client = UsuarioRol(
                    usuario_id=result.id,
                    rol_codigo="CLIENT",
                    asignado_por_id=result.id
            )
            
            uow.usuarios.add_rol(rol_client)

            return UserResponse(
                id=result.id,
                nombre=result.nombre,
                apellido=result.apellido,
                email=result.email,
                roles=["CLIENT"],
                created_at=result.created_at,
            )


    def login(self, user_in: LoginRequest) -> TokenResponse:
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_email(user_in.email)

            if not user or not verify_password(user_in.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales incorrectas",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if user.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cuenta de usuario desactivada",
                )

            roles = self._usuario_roles(user)
            access_token = create_access_token(data={"sub": user.email, "roles": roles})
            refresh_token = generate_refresh_token()
            refresh_hash = hash_refresh_token(refresh_token)
            expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            uow.refresh_tokens.create(refresh_hash, user.id, expires_at)

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )


    def authenticate(self, username: str, password: str) -> TokenResponse:
        return self.login(LoginRequest(email=username, password=password))


    def refresh(self, refresh_in: RefreshRequest) -> TokenResponse:
        token_hash = hash_refresh_token(refresh_in.refresh_token)

        with UsuarioUnitOfWork(self._session) as uow:
            refresh_token = uow.refresh_tokens.get_active_by_hash(token_hash)

            if refresh_token is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token inválido o expirado",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            usuario = uow.usuarios.get_by_id(refresh_token.usuario_id)

            if usuario is None or usuario.deleted_at is not None:
                uow.refresh_tokens.revoke(token_hash)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token inválido o expirado",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            roles = self._usuario_roles(usuario)
            uow.refresh_tokens.revoke(token_hash)

            new_refresh = generate_refresh_token()
            new_refresh_hash = hash_refresh_token(new_refresh)
            expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            uow.refresh_tokens.create(new_refresh_hash, usuario.id, expires_at)

            return TokenResponse(
                access_token=create_access_token(data={"sub": usuario.email, "roles": roles}),
                refresh_token=new_refresh,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )


    def logout(self, user_id: int, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)

        with UsuarioUnitOfWork(self._session) as uow:
            token = uow.refresh_tokens.get_active_by_hash(token_hash)

            if token is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token inválido o expirado",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if token.usuario_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="El refresh token no pertenece al usuario autenticado",
                )

            uow.refresh_tokens.revoke(token_hash)


    def get_me(self, user_id: int) -> UserResponse:
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_id(user_id)

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado",
                )

            return self._to_user_response(user)


    def list_all(self, rol: Optional[str], offset: int, limit: int) -> list[UserPublic]:
        with UsuarioUnitOfWork(self._session) as uow:
            usuarios = uow.usuarios.get_all_usuarios(rol=rol, offset=offset, limit=limit)
            result = [self._to_user_public(u) for u in usuarios]

        return result


    def set_disabled(self, user_id: int, disabled: bool) -> UserPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_id(user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado",
                )
            
            user_deleted = user.deleted_at is not None
            
            if user_deleted == disabled:
                estado = "desactivado" if disabled else "activo"

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El usuario ya se encuentra {estado}",
                )

                
            user.deleted_at = datetime.now(timezone.utc) if disabled else None
            user.updated_at = datetime.now(timezone.utc)
            updated = uow.usuarios.add(user)

            return self._to_user_public(updated)