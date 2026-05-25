from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.direcciones.repository import DireccionRepository
from app.modules.pedido.repository import PedidoRepository
from app.modules.producto.repository import ProductoRepository

class PedidoUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.pedidos = PedidoRepository(session)
        self.productos = ProductoRepository(session)
        self.direcciones = DireccionRepository(session)
