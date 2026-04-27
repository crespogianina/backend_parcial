from sqlmodel import Session, func, null, select
from app.core.repository import BaseRepository
from app.modules.ingrediente.models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    def get_by_nombre(self, nombre: str) -> Ingrediente | None:
        return self.session.exec(select(Ingrediente).where(func.lower(Ingrediente.nombre) == nombre.lower())).first()

    def get_ingredientes_existentes(self, offset: int = 0, limit: int = 20) -> list[Ingrediente]:
        return list(
            self.session.exec(
                select(Ingrediente)
                .where(Ingrediente.deleted_at.is_(None))
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count(self) -> int:
        return len(self.session.exec(select(Ingrediente)).all())
    
    def count_ingredientes_existentes(self) -> int:
        return len(self.session.exec(select(Ingrediente).where(Ingrediente.deleted_at.is_(None))).all())