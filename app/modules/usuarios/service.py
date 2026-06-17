from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session
from app.core.config import settings
from app.core.security import decode_token_con_motivo, hash_password, verify_password, create_access_token
from app.modules.usuarios.model import Usuario, UsuarioRol
from app.modules.usuarios.schemas import UserCreate, Token, UserPublic, UserUpdate
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork


class UsuarioService:

    def __init__(self, session: Session):
        self._session = session

    # ── Helpers ──────────────────────────────────────────────────────

    def autenticar_websocket(self, token: str) -> tuple[Optional[tuple[int, str]], str]:
        try:
            payload, motivo = decode_token_con_motivo(token)

            if payload is None:
                return None, motivo

            username = payload.get("sub")

            if not username:
                return None, "invalido"

            with UsuarioUnitOfWork(self._session) as uow:
                user = uow.usuarios.get_by_username(username)

                if not user or user.deleted_at is not None:
                    return None

                roles = [ur.rol_codigo for ur in user.usuario_roles]

                return (user.id, roles)
        except Exception as e:
            print("ERROR WS:", e)
            raise
        
    # ────────────────────────────────────────────────────────

    def get_by_username(self, username: str) -> UserPublic | None:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = uow.usuarios.get_by_username(username)

            if not usuario:
                return None

            return UserPublic(**usuario.model_dump(), roles=[ur.rol_codigo for ur in usuario.usuario_roles])


    def register(self, user_in: UserCreate) -> UserPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario_existe = uow.usuarios.get_by_username(user_in.username)

            if usuario_existe:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El nombre de usuario ya está en uso",
                )

            email_existe = uow.usuarios.get_by_email(user_in.email)

            if email_existe:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El email ya está registrado",
                )

            usuario = Usuario(
                username=user_in.username,
                nombre=user_in.nombre,
                apellido=user_in.apellido,
                email=user_in.email,
                celular=user_in.celular,
                password_hash=hash_password(user_in.password),
            )

            result = uow.usuarios.add(usuario)

            rol_client = UsuarioRol(
                    usuario_id=result.id,
                    rol_codigo="CLIENT",
                    asignado_por_id=result.id
            )
            
            uow.usuarios.add_rol(rol_client)

            return UserPublic(**result.model_dump(), roles=["CLIENT"])


    def authenticate(self, username: str, password: str) -> Token:
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_username(username)

            if not user or not verify_password(password, user.password_hash):
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

            roles = [ur.rol_codigo for ur in user.usuario_roles]

            access_token = create_access_token(data={"sub": user.username, "roles": roles})
            
            return Token(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )


    def list_all(self, rol: Optional[str] = None, nombre: Optional[str] = None, email: Optional[str] = None, offset: int = 0, limit: int = 50) -> list[UserPublic]:
        with UsuarioUnitOfWork(self._session) as uow:
            usuarios = uow.usuarios.get_all_usuarios(rol=rol, nombre=nombre, email=email, offset=offset, limit=limit)
            result = [UserPublic(**u.model_dump(), roles=[ur.rol_codigo for ur in u.usuario_roles]) for u in usuarios] 

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

                
            user.deleted_at = datetime.now() if disabled else None
            updated = uow.usuarios.add(user)

            return UserPublic(**updated.model_dump(), roles=[ur.rol_codigo for ur in updated.usuario_roles])

    def update_me(self, user_id: int, data: UserUpdate) -> UserPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_id(user_id)

            if not user or user.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado",
                )

            updates = data.model_dump(exclude_unset=True)

            if not updates:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No hay datos para actualizar",
                )

            if "nombre" in updates:
                nombre = updates["nombre"].strip()
                if not nombre:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="El nombre no puede estar vacío",
                    )
                user.nombre = nombre

            if "apellido" in updates:
                apellido = updates["apellido"].strip()
                if not apellido:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="El apellido no puede estar vacío",
                    )
                user.apellido = apellido

            if "email" in updates:
                email = str(updates["email"]).strip().lower()
                otro = uow.usuarios.get_by_email(email)
                if otro and otro.id != user.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="El email ya está registrado",
                    )
                user.email = email

            if "celular" in updates:
                celular = updates["celular"]
                user.celular = celular.strip() if celular and celular.strip() else None

            user.updated_at = datetime.now(timezone.utc)
            updated = uow.usuarios.add(user)

            return UserPublic(
                **updated.model_dump(),
                roles=[ur.rol_codigo for ur in updated.usuario_roles],
            )