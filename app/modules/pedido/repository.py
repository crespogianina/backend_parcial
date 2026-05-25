from datetime import date, datetime, time
from typing import Optional
from sqlalchemy import Select, func
from sqlmodel import Session, select
from app.core.repository import BaseRepository
from app.modules.pedido.models import DetallePedido, FormaPago, HistorialEstadoPedido, Pedido
from app.modules.pedido.schemas import PedidoDetail

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



class FormaPagoRepository(BaseRepository[FormaPago]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, FormaPago)

    def get_habilitada(self, codigo: str) -> FormaPago | None:
        return self.session.exec(
            select(FormaPago)
            .where(FormaPago.codigo == codigo)
            .where(FormaPago.habilitado == True)
        ).first()


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
            statement = statement.where(Pedido.estado_codigo  == estado)

        if usuario_id is not None:
            statement = statement.where(Pedido.usuario_id == usuario_id)

        if fecha_desde is not None:
            statement = statement.where(Pedido.created_at >= datetime.combine(fecha_desde, time.min))

        if fecha_hasta is not None:
            statement = statement.where(Pedido.created_at <= datetime.combine(fecha_hasta, time.max))

        return statement

    ############################################################ 

    def get_all_pedidos(
            self,
            usuario_id: Optional[int] = None,
            estado: Optional[str] = None,
            fecha_desde: Optional[date] = None,
            fecha_hasta: Optional[date] = None,
            offset: int = 0, 
            limit: int = 50
        ) -> list[PedidoDetail]:
        statement = self._apply_filters(select(Pedido), estado, usuario_id, fecha_desde, fecha_hasta)
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