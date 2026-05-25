from typing import Optional
from sqlalchemy import Select
from sqlmodel import Session, func, select
from app.core.repository import BaseRepository
from app.modules.categoria.models import Categoria

class CategoriaRepository(BaseRepository[Categoria]):
    
    def __init__(self, session: Session) -> None:
        super().__init__(session, Categoria)

    ######### Helper filtros #######

    def _apply_filters(
        self,
        statement: Select,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        parent_id: Optional[int] = None
    ) -> Select:
        if nombre is not None:
            statement = statement.where(Categoria.nombre.ilike(f"%{nombre}%"))

        if descripcion is not None:
            statement = statement.where(Categoria.descripcion.ilike(f"%{descripcion}%"))

        if parent_id is not None:
            statement = statement.where(Categoria.parent_id == parent_id)

        return statement
    
    ############################################################ 

    def get_by_name(self, nombre: str) -> Categoria | None:
        statement = select(Categoria).where(func.lower(Categoria.nombre) == nombre.lower())

        return self.session.exec(statement).first()


    def get_all_categorias(
            self, 
            nombre: Optional[str] = None, 
            descripcion: Optional[str] = None, 
            parent_id: Optional[int] = None,
            offset: int = 0, 
            limit: int = 50
        ) -> list[Categoria]:
        statement = self._apply_filters(select(Categoria), nombre, descripcion, parent_id)
        statement = statement.order_by(Categoria.nombre)

        return list(self.session.exec(statement.offset(offset).limit(limit)).all())


    def get_categoria_tree(self) -> list[Categoria]:
        statement = select(Categoria).order_by(Categoria.nombre)

        return list( self.session.exec(statement).all())


    def count_all_categorias(self, nombre: Optional[str] = None, descripcion: Optional[str] = None, parent_id: Optional[int] = None) -> int:
        statement = self._apply_filters(select(func.count()).select_from(Categoria), nombre, descripcion, parent_id)

        return self.session.exec(statement).one()