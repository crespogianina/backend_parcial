from sqlmodel import Session, func, select
from typing import Optional
from app.core.repository import BaseRepository
from app.modules.ingrediente.models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    def get_by_nombre(self, nombre: str) -> Ingrediente | None:
        return self.session.exec(select(Ingrediente).where(func.lower(Ingrediente.nombre) == nombre.lower())).first()

    def get_ingredientes_existentes(self, offset: int = 0, limit: int = 20, es_alergeno: Optional[bool] = None) -> list[Ingrediente]:
        statement = select(Ingrediente).where(Ingrediente.deleted_at.is_(None))

        if es_alergeno is not None:
            statement = statement.where(Ingrediente.es_alergeno == es_alergeno)

        return list(self.session.exec(statement.offset(offset).limit(limit)).all())

    def get_ingredientes_alergenos(self, offset: int = 0, limit: int = 20) -> list[Ingrediente]:
        return list(
            self.session.exec(
                select(Ingrediente)
                .where(Ingrediente.deleted_at.is_(None))
                .where(Ingrediente.es_alergeno == True)
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count(self) -> int:
        return len(self.session.exec(select(Ingrediente)).all())

    def count_ingredientes_existentes(self) -> int:
        return len(self.session.exec(select(Ingrediente).where(Ingrediente.deleted_at.is_(None))).all())