from typing import List, Optional
from sqlalchemy import Select
from sqlmodel import Session, func, select
from app.core.repository import BaseRepository
from app.modules.producto.models import Producto, ProductoCategoria,ProductoIngrediente, UnidadMedida
from app.modules.categoria.models import Categoria
from app.modules.ingrediente.models import Ingrediente 
from sqlalchemy.orm import selectinload

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
        categoria_id: Optional[int] = None
    ) -> Select:
        if nombre is not None:
            statement = statement.where(Producto.nombre.ilike(f"%{nombre}%"))

        if descripcion is not None:
            statement = statement.where(Producto.descripcion.ilike(f"%{descripcion}%"))

        if disponible is not None:
            statement = statement.where(Producto.disponible == disponible)

        if categoria_id is not None:
            statement = (
                statement
                .join(ProductoCategoria, ProductoCategoria.producto_id == Producto.id)
                .where(ProductoCategoria.categoria_id == categoria_id)
            )

        return statement
    
    ############################################################ 


    def get_by_nombre(self, nombre: str) -> Producto | None:
        statement = select(Producto).where(func.lower(Producto.nombre) == nombre.lower())

        return self.session.exec(statement).first()


    def get_with_lock(self, producto_id: int) -> Producto | None:
        statement = (
            select(Producto)
            .where(Producto.id == producto_id)
            .where(Producto.deleted_at.is_(None))
            .with_for_update()
        )
        
        return self.session.exec(statement).first()


    def get_all_productos(
            self,
            nombre: Optional[str] = None, 
            descripcion: Optional[str] = None,
            disponible: Optional[bool] = None,
            categoria_id: Optional[int] = None,
            offset: int = 0, 
            limit: int = 50
        ) -> list[Producto]:
        statement = self._apply_filters(
            select(Producto),
            nombre,
            descripcion,
            disponible,
            categoria_id
        ).options(
            selectinload(Producto.unidad_medida),
            selectinload(Producto.producto_categorias).selectinload(ProductoCategoria.categoria),
            selectinload(Producto.producto_ingredientes).selectinload(ProductoIngrediente.ingrediente),
        )
        
        statement = statement.offset(offset).limit(limit).order_by(Producto.nombre.asc())

        return list(self.session.exec(statement).all())


    def count_all_productos(self,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        disponible: Optional[bool] = None,
        categoria_id: Optional[int] = None,
    ) -> int:
        statement = self._apply_filters(
            select(func.count()).select_from(Producto),
            nombre, descripcion, disponible, categoria_id
        )

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


    def get_unidad_medida(self, unidad_medida_id: int) -> UnidadMedida:
        return self.session.get(UnidadMedida, unidad_medida_id)


    def get_all_unidad_medida(self) -> list[UnidadMedida]:
        return self.session.exec(select(UnidadMedida)).all()

    def get_removibles_ids(self, producto_id: int) -> set[int]:
        rows = self._session.exec(
            select(ProductoIngrediente.ingrediente_id)
            .where(ProductoIngrediente.producto_id == producto_id)
            .where(ProductoIngrediente.es_removible == True)
        ).all()
        return set(rows)