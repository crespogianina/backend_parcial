from typing import List

from sqlmodel import Session, func, null, select
from app.core.repository import BaseRepository
from app.modules.producto.models import Producto, ProductoCategoria
from app.modules.categoria.models import Categoria


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
        return len(self.session.exec(select(Producto)).all())
    
    def get_categorias_by_producto(self, producto_id: int) -> List[Categoria]:
        statement = (
            select(Categoria)
            .join(
                ProductoCategoria,
                ProductoCategoria.categoria_id == Categoria.id
            )
            .where(ProductoCategoria.producto_id == producto_id)
        )

        return list(self.session.exec(statement).all())