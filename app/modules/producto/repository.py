from typing import List, Optional

from sqlalchemy import Select
from sqlmodel import Session, func, select
from app.core.repository import BaseRepository
from app.modules.producto.models import Producto, ProductoCategoria,ProductoIngrediente
from app.modules.categoria.models import Categoria
from app.modules.ingrediente.models import Ingrediente 


class ProductoRepository(BaseRepository[Producto]):
    
    def __init__(self, session: Session) -> None:
        super().__init__(session, Producto)

 ######### Helper filtros #######

    def _apply_filters(
        self,
        statement: Select,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        disponible: Optional[bool] = None,
    ) -> Select:
        if nombre is not None:
            statement = statement.where(Producto.nombre.ilike(f"%{nombre}%"))

        if descripcion is not None:
            statement = statement.where(Producto.descripcion.ilike(f"%{descripcion}%"))

        if disponible is not None:
            statement = statement.where(Producto.disponible == disponible)

        return statement
    
    ############################################################ 


    def get_by_nombre(self, nombre: str) -> Producto | None:
        statement = select(Producto).where(func.lower(Producto.nombre) == nombre.lower())

        return self.session.exec(statement).first()


    def get_all_productos(
            self,
            nombre: Optional[str] = None, 
            descripcion: Optional[str] = None,
            disponible: Optional[bool] = None,
            offset: int = 0, 
            limit: int = 20
        ) -> list[Producto]:
        statement = self._apply_filters(select(Producto), nombre, descripcion, disponible)
        statement = statement.offset(offset).limit(limit).order_by(Producto.nombre.desc())

        return list(self.session.exec(statement).all())


    def count_all_productos(self,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        disponible: Optional[bool] = None
    ) -> int:
        statement =self._apply_filters(select(func.count()).select_from(Producto), nombre, descripcion, disponible)

        return self.session.exec(statement).one()
    

    def get_categorias_by_producto(self, producto_id: int) -> List[Categoria]:
        statement = (
            select(Categoria)
            .join(
                ProductoCategoria,
                ProductoCategoria.categoria_id == Categoria.id
            )
            .where(ProductoCategoria.producto_id == producto_id)
            .where(Categoria.deleted_at.is_(None))
        )

        return list(self.session.exec(statement).all())


    def get_ingredientes_by_producto(self, producto_id: int) -> List[Ingrediente]:
        statement = (
            select(Ingrediente)
            .join(
                ProductoIngrediente,
                ProductoIngrediente.ingrediente_id == Ingrediente.id
            )
            .where(ProductoIngrediente.producto_id == producto_id)
            .where(Ingrediente.deleted_at.is_(None))
        )

        return list(self.session.exec(statement).all())


    def delete_categorias_by_producto(self, producto_id: int) -> None:
        links = self.session.exec(select(ProductoCategoria).where(ProductoCategoria.producto_id == producto_id)).all()

        for link in links:
            self.session.delete(link)

        self.session.flush()


    def delete_ingredientes_by_producto(self, producto_id: int) -> None:        
        links = self.session.exec(select(ProductoIngrediente).where(ProductoIngrediente.producto_id == producto_id)).all()

        for link in links:
            self.session.delete(link)

        self.session.flush()
