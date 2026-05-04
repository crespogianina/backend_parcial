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
            nombre: Optional[str] = None, 
            descripcion: Optional[str] = None, 
            offset: int = 0, 
            limit: int = 20
            ) -> list[Categoria]:

        statement = select(Categoria).where(Categoria.deleted_at.is_(None))

        if nombre is not None:
            statement = statement.where(Categoria.nombre.ilike(f"%{nombre}%"))

        if descripcion is not None:
            statement = statement.where(Categoria.descripcion.ilike(f"%{descripcion}%"))

        statement = statement.order_by(
            Categoria.updated_at.desc()
        )

        return list(self.session.exec(statement.offset(offset).limit(limit)).all())

    def get_categoria_tree(self) -> list[Categoria]:
        return list(
            self.session.exec(select(Categoria).where(Categoria.deleted_at.is_(None)).order_by(Categoria.nombre)).all()
        )

    def count_all_categorias(self) -> int:
        statement = select(func.count()).select_from(Categoria).where(Categoria)
        return self.session.exec(statement).one()

    def count_categorias_existentes(self, nombre: Optional[str] = None, descripcion: Optional[str] = None) -> int:
        statement = select(func.count()).select_from(Categoria).where(Categoria.deleted_at.is_(None))
        
        if nombre is not None:
            statement = statement.where(Categoria.nombre.ilike(f"%{nombre}%"))

        if descripcion is not None:
            statement = statement.where(Categoria.descripcion.ilike(f"%{descripcion}%"))

        return self.session.exec(statement).one()