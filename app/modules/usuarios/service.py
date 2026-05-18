from fastapi import HTTPException, status
from sqlmodel import Session
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.modules.usuarios.model import Usuario
from app.modules.usuarios.schemas import UserCreate, Token, UserPublic
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork


class UsuarioService:

    def __init__(self, session: Session):
        self._session = session


    def get_by_username(self, username: str) -> Usuario | None:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = uow.usuarios.get_by_username(username) 

        return usuario 

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
                full_name=user_in.full_name,
                email=user_in.email,
                hashed_password=hash_password(user_in.password),
                role="user",
            )

            usuario_creado = uow.usuarios.add(usuario)

            return UserPublic.model_validate(usuario_creado)

    def authenticate(self, username: str, password: str) -> Token:
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_username(username)

            if not user or not verify_password(password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales incorrectas",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if user.disabled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cuenta de usuario desactivada",
                )

            access_token = create_access_token(
                data={"sub": user.username, "role": user.role}
            )
            
            return Token(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

    def list_all(self) -> list[UserPublic]:
        with UsuarioUnitOfWork(self._session) as uow:
            usuarios = uow.usuarios.get_all()
            result =[UserPublic.model_validate(u) for u in usuarios] 

        return result


    def set_disabled(self, user_id: int, disabled: bool) -> UserPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_id(user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado",
                )
            
            if user.disabled == disabled:
                estado = "desactivado" if disabled else "activado"

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El usuario ya se encuentra {estado}",
                )
                
            user.disabled = disabled
            updated = uow.usuarios.add(user)
            result = UserPublic.model_validate(updated) 
            
        return result
