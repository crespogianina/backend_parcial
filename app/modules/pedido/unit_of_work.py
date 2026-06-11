from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.direcciones.repository import DireccionRepository
from app.modules.pedido.repository import DetallePedidoRepository, FormaPagoRepository, HistorialEstadoPedidoRepository, PedidoRepository
from app.modules.producto.repository import ProductoRepository
from app.modules.usuarios.repository import UsuarioRepository

class PedidoUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.pedidos = PedidoRepository(session)
        self.productos = ProductoRepository(session)
        self.direcciones = DireccionRepository(session)
        self.detalles   = DetallePedidoRepository(session)
        self.historial  = HistorialEstadoPedidoRepository(session) 
        self.formas_pago  = FormaPagoRepository(session) 
        self.usuarios  = UsuarioRepository(session) 