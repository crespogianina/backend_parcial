from typing import Optional

from sqlmodel import Session, func, select
from app.core.repository import BaseRepository
from app.modules.categoria.models import Categoria


class CategoriaRepository(BaseRepository[Categoria]):
    
    def __init__(self, session: Session) -> None:
        super().__init__(session, Categoria)

    def get_by_name(self, nombre: str) -> Categoria | None:
        return self.session.exec(select(Categoria).where(func.lower(Categoria.nombre) == nombre.lower())).first()

    def get_categorias_existentes(
        self,
        es_raiz: Optional[bool] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Categoria]:
        statement = select(Categoria).where(Categoria.deleted_at.is_(None))

        if es_raiz is True:
            statement = statement.where(Categoria.parent_id.is_(None))
        elif es_raiz is False:
            statement = statement.where(Categoria.parent_id.is_not(None))

        return list(self.session.exec(statement.offset(offset).limit(limit)).all())

    def get_categoria_tree(self) -> list[Categoria]:
        return list(
            self.session.exec(select(Categoria).where(Categoria.deleted_at.is_(None)).order_by(Categoria.nombre)).all()
        )

    def count_all_categorias(self) -> int:
        statement = select(func.count()).select_from(Categoria).where(Categoria)
        return self.session.exec(statement).one()

    def count_categorias_existentes(self, es_raiz: Optional[bool] = None) -> int:
        statement = select(func.count()).select_from(Categoria).where(Categoria.deleted_at.is_(None))

        if es_raiz is True:
            statement = statement.where(Categoria.parent_id.is_(None))
        elif es_raiz is False:
            statement = statement.where(Categoria.parent_id.is_not(None))

        return self.session.exec(statement).one()