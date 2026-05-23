
from zipfile import Path

from typing_extensions import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.modules.pedido.schemas import PedidoCreate, PedidoRead, PedidoDetail, DetallePedidoRead
from app.modules.pedido.service import PedidoService


router = APIRouter(dependencies=[Depends(get_current_active_user)])


def get_pedido_service(session: Session = Depends(get_session)) -> PedidoService:
    return PedidoService(session)


# Endpoints
@router.post("/", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def register(pedido_in: PedidoCreate, svc: PedidoService = Depends(get_pedido_service)) -> PedidoRead:
    return svc.register(pedido_in)


@router.get("/", response_model=list[PedidoRead], status_code=status.HTTP_201_CREATED)
def list_pedidos( svc: PedidoService = Depends(get_pedido_service)) -> list[PedidoRead]:
    return svc.get_pedido()


@router.get("/{id}", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def get_pedido(id: Annotated[int, Path(gt=0)], svc: PedidoService = Depends(get_pedido_service)) -> PedidoRead:
    return svc.get_pedido_id(id)


@router.put("/{id}", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def update_pedido(id: Annotated[int, Path(gt=0)], pedido_in: PedidoCreate, svc: PedidoService = Depends(get_pedido_service)) -> PedidoRead:
    return svc.update_pedido(id, pedido_in)


@router.patch("/{id}", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def update_pedido(id: Annotated[int, Path(gt=0)], pedido_in: PedidoCreate, svc: PedidoService = Depends(get_pedido_service)) -> PedidoRead:
    return svc.update_pedido(id, pedido_in)


@router.delete("/{id}", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def delete_pedido(id: Annotated[int, Path(gt=0)], svc: PedidoService = Depends(get_pedido_service)) -> PedidoRead:
    return svc.delete_pedido(id)
