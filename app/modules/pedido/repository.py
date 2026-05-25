from datetime import date
from typing import Optional

from sqlalchemy import Select, func
from sqlmodel import Session, select
from app.core.repository import BaseRepository
from app.modules.ingrediente.models import Ingrediente
from app.modules.pedido.models import DetallePedido, HistorialEstadoPedido, Pedido
from app.modules.pedido.schemas import PedidoDetail
from app.modules.producto.models import Producto

class DetallePedidoRepository(BaseRepository[DetallePedido]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DetallePedido)

    def add_all(self, items: list) -> None:
        for item in items:
            self.session.add(item)
        self.session.flush()

class HistorialEstadoPedidoRepository(BaseRepository[HistorialEstadoPedido]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, HistorialEstadoPedido)


class PedidoRepository(BaseRepository[Pedido]):
    
    def __init__(self, session: Session):
        super().__init__(session, Pedido)

######### Helper filtros #######

    def _apply_filters(
        self,
        statement: Select,
        estado: Optional[str] = None,
        usuario_id: Optional[int] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
    ) -> Select:
        if estado is not None:
            statement = statement.where(Pedido.estado == estado)

        if usuario_id is not None:
            statement = statement.where(Pedido.usuario_id == usuario_id)

        if fecha_desde is not None:
            statement = statement.where(Pedido.created_at >= fecha_desde)

        if fecha_hasta is not None:
            statement = statement.where(Pedido.created_at <= fecha_hasta)

        return statement

    ############################################################ 

    def get_all_pedidos(
            self,
            usuario_id: Optional[int] = None,
            estado: Optional[str] = None,
            fecha_desde: Optional[date] = None,
            fecha_hasta: Optional[date] = None,
            offset: int = 0, 
            limit: int = 20
        ) -> list[PedidoDetail]:
        statement = self._apply_filters(select(Pedido), usuario_id, estado, fecha_desde, fecha_hasta)
        statement = statement.order_by(Pedido.created_at.desc())

        return list(self.session.exec(statement.offset(offset).limit(limit)).all())

    def count_all_pedidos(
            self, 
            usuario_id: Optional[int] = None,
            estado: Optional[str] = None,
            fecha_desde: Optional[date] = None,
            fecha_hasta: Optional[date] = None
        ) -> int:
        statement = self._apply_filters(select(func.count()).select_from(Pedido), usuario_id, estado, fecha_desde, fecha_hasta)
        return self.session.exec(statement).one()