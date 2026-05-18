from sqlmodel import Session, func, select
from typing import Optional
from app.core.repository import BaseRepository
from app.modules.ingrediente.models import Ingrediente
from sqlalchemy import Select

class IngredienteRepository(BaseRepository[Ingrediente]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    ######### Helper filtros #######

    def _apply_filters(
        self,
        statement: Select,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        es_alergeno: Optional[bool] = None,
    ) -> Select:
        if nombre is not None:
            statement = statement.where(Ingrediente.nombre.ilike(f"%{nombre}%"))

        if descripcion is not None:
            statement = statement.where(Ingrediente.descripcion.ilike(f"%{descripcion}%"))

        if es_alergeno is not None:
            statement = statement.where(Ingrediente.es_alergeno == es_alergeno)

        return statement
    
    ############################################################ 

    def get_by_nombre(self, nombre: str) -> Ingrediente | None:
        statement = select(Ingrediente).where(func.lower(Ingrediente.nombre) == nombre.lower())

        return self.session.exec(statement).first()


    def get_all_ingredientes(
            self,
            nombre: Optional[str] = None,
            descripcion: Optional[str] = None,
            es_alergeno: Optional[bool] = None,
            offset: int = 0, 
            limit: int = 20
        ) -> list[Ingrediente]:
        statement = self._apply_filters(select(Ingrediente), nombre, descripcion, es_alergeno)
        statement = statement.order_by(Ingrediente.nombre.desc())

        return list(self.session.exec(statement.offset(offset).limit(limit)).all())


    def count_all_ingredientes(
            self, 
            nombre: Optional[str] = None, 
            descripcion: Optional[str] = None, 
            es_alergeno: Optional[bool] = None
        ) -> int:
        statement = self._apply_filters(select(func.count()).select_from(Ingrediente), nombre, descripcion, es_alergeno)
        return self.session.exec(statement).one()