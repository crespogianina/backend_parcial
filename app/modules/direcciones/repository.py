from sqlalchemy import Select
from sqlmodel import Session, func, select

from app.core.repository import BaseRepository
from app.modules.direcciones.model import DireccionEntrega

class DireccionRepository(BaseRepository[DireccionEntrega]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, DireccionEntrega)


    def _active_for_user(self, usuario_id: int) -> Select:
        return (
            select(DireccionEntrega)
            .where(DireccionEntrega.usuario_id == usuario_id)
            .where(DireccionEntrega.deleted_at.is_(None))
        )


    def get_by_id_for_user(self, direccion_id: int, usuario_id: int) -> DireccionEntrega | None:
        statement = self._active_for_user(usuario_id).where(DireccionEntrega.id == direccion_id)
        return self.session.exec(statement).first()


    def get_all_for_user(
        self,
        usuario_id: int,
        offset: int = 0,
        limit: int = 50,
    ) -> list[DireccionEntrega]:
        statement = (
            self._active_for_user(usuario_id)
            .order_by(DireccionEntrega.es_principal.desc(), DireccionEntrega.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        return list(self.session.exec(statement).all())


    def count_active_for_user(self, usuario_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(DireccionEntrega)
            .where(DireccionEntrega.usuario_id == usuario_id)
            .where(DireccionEntrega.deleted_at.is_(None))
        )

        return self.session.exec(statement).one()


    def clear_principal_for_user(self, usuario_id: int) -> None:
        statement = self._active_for_user(usuario_id).where(DireccionEntrega.es_principal.is_(True))
        for direccion in self.session.exec(statement).all():
            direccion.es_principal = False
            self.session.add(direccion)
        self.session.flush()


    def get_first_active_for_user(self, usuario_id: int) -> DireccionEntrega | None:
        statement = self._active_for_user(usuario_id).order_by(DireccionEntrega.created_at.asc())
        return self.session.exec(statement).first()