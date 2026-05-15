from fastapi import HTTPException, status
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.core.uow import UnitOfWork
from app.modules.usuarios.model import Usuario, UserCreate, Token, UserPublic


class UsuarioService:

    def __init__(self, session: Session):
        self.session = session


    ##########################################

    def register(self, user_in: UserCreate) -> UserPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            usuarioExiste = uow.usuarios.get_by_username(usuario.username)
            if usuarioExiste:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El nombre de usuario ya está en uso",
                )
                
            usuarioExiste = uow.usuarios.get_by_email(usuario.username)                
            if usuarioExiste:
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
    
            usuario = UserPublic.model_validate(uow.usuarios.add(usuario))
            return usuario

    def authenticate(self, username: str, password: str) -> Token:
        with CategoriaUnitOfWork(self._session) as uow:
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

    def list_all(self) -> list[Usuario]:
        with CategoriaUnitOfWork(self._session) as uow:
            return uow.usuarios.get_all()

    def set_disabled(self, user_id: int, disabled: bool) -> UserPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_id(user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado",
                )
                
            user.disabled = disabled
            
            return uow.usuarios.add(user)
