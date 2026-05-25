from typing import Optional

from sqlmodel import Session, select
from app.core.repository import BaseRepository
from app.modules.usuarios.model import Usuario, UsuarioRol


class UsuarioRepository(BaseRepository[Usuario]):

    def __init__(self, session: Session):
        super().__init__(session, Usuario)

    def get_by_username(self, username: str) -> Usuario | None:
        statement = select(Usuario).where(Usuario.username == username) 
        
        return self.session.exec(statement).first()


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
            )

        return list(self.session.exec(statement.offset(offset).limit(limit)).all())
