from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select
from app.core.repository import BaseRepository
from app.modules.usuarios.model import RefreshToken, Usuario, UsuarioRol


class UsuarioRepository(BaseRepository[Usuario]):

    def __init__(self, session: Session):
        super().__init__(session, Usuario)


    def get_by_email(self, email: str) -> Usuario | None:
        statement = select(Usuario).where(Usuario.email == email) 

        return self.session.exec(statement).first()


    def add_rol(self, usuario_rol: UsuarioRol) -> UsuarioRol:
        self.session.add(usuario_rol)
        self.session.flush()
        
        return usuario_rol
    

    def get_all_usuarios(self, rol: Optional[str] = None, offset: int = 0, limit: int = 50) -> list[Usuario]:
        statement = select(Usuario)

        if rol:
            statement = (
                statement
                .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
                .where(UsuarioRol.rol_codigo == rol)
                .distinct()
            )

        return list(self.session.exec(statement.offset(offset).limit(limit)).all())


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: Session):
        super().__init__(session, RefreshToken)

    def create(self, token_hash: str, usuario_id: int, expires_at: datetime) -> RefreshToken:
        refresh_token = RefreshToken(
            token_hash=token_hash,
            usuario_id=usuario_id,
            expires_at=expires_at,
        )
        self.session.add(refresh_token)
        self.session.flush()
        return refresh_token

    def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        now = datetime.now(timezone.utc)
        statement = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.revoked_at.is_(None))
            .where(RefreshToken.expires_at > now)
        )
        return self.session.exec(statement).first()

    def revoke(self, token_hash: str) -> RefreshToken | None:
        refresh_token = self.get_active_by_hash(token_hash)

        if refresh_token is None:
            return None

        refresh_token.revoked_at = datetime.now(timezone.utc)
        self.session.add(refresh_token)
        self.session.flush()
        return refresh_token
