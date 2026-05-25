# app/modules/pedido/router.py

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.modules.pedido.schemas import PedidoCreate, PedidoDetail
from app.modules.pedido.service import PedidoService
from app.modules.pedido.unit_of_work import PedidoUnitOfWork
from app.modules.producto.service import ProductoService
from app.modules.usuarios.schemas import UserPublic

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


# ── Dependencias ──────────────────────────────────────────────────────────────

def get_producto_service(
    session: Session = Depends(get_session),
) -> ProductoService:
    return ProductoService(session)


def get_pedido_service(
    session: Session = Depends(get_session),
    producto_service: ProductoService = Depends(get_producto_service),
) -> PedidoService:
    return PedidoService(PedidoUnitOfWork(session), producto_service)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=PedidoDetail,
    status_code=status.HTTP_201_CREATED,
)
def crear_pedido(
    data: PedidoCreate,
    usuario: UserPublic = Depends(get_current_active_user),
    service: PedidoService = Depends(get_pedido_service),
) -> PedidoDetail:
    return service.crear_pedido(usuario.id, data)