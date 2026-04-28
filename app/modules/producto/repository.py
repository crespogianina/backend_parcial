from typing import List

from sqlmodel import Session, func, null, select
from app.core.repository import BaseRepository
from app.modules.producto.models import Producto, ProductoCategoria,ProductoIngrediente
from app.modules.categoria.models import Categoria
from app.modules.ingrediente.models import Ingrediente 


class ProductoRepository(BaseRepository[Producto]):
    
    def __init__(self, session: Session) -> None:
        super().__init__(session, Producto)

    def get_by_nombre(self, nombre: str) -> Producto | None:
        return self.session.exec(select(Producto).where(func.lower(Producto.nombre) == nombre.lower())).first()

    def get_productos_existentes(self, offset: int = 0, limit: int = 20) -> list[Producto]:
        return list(
            self.session.exec(
                select(Producto)
                .where(Producto.deleted_at.is_(None))
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count_productos_existentes(self) -> int:
        statement = select(func.count()).select_from(Producto).where(Producto.deleted_at.is_(None))
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
        links = self.session.exec(
            select(ProductoCategoria).where(ProductoCategoria.producto_id == producto_id)
        ).all()
        for link in links:
            self.session.delete(link)
        self.session.flush()

    def delete_ingredientes_by_producto(self, producto_id: int) -> None:
        from app.modules.producto.models import ProductoIngrediente
        links = self.session.exec(
            select(ProductoIngrediente).where(ProductoIngrediente.producto_id == producto_id)
        ).all()
        for link in links:
            self.session.delete(link)
        self.session.flush()
