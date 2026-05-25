# app/modules/pedido/router.py
from datetime import date
from typing import Optional
from typing_extensions import Annotated
from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlmodel import Session
from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.modules.pedido.schemas import (
    AvanzarEstadoRequest,
    PedidoCreate,
    PedidoDetail,
    PedidoListResponse,
)
from app.modules.pedido.service import PedidoService
from app.modules.usuarios.schemas import UserPublic

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


# ── Dependencias ──────────────────────────────────────────────────────────────

def get_pedido_service(session: Session = Depends(get_session)) -> PedidoService:
    return PedidoService(session)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=PedidoDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido",
)
def crear_pedido(
    data: PedidoCreate,
    usuario: UserPublic = Depends(get_current_active_user),
    service: PedidoService = Depends(get_pedido_service),
) -> PedidoDetail:
    return service.crear_pedido(usuario.id, data)


@router.get(
    "/",
    response_model=PedidoListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar pedidos",
)
def obtener_pedidos(
    usuario: UserPublic = Depends(get_current_active_user),
    service: PedidoService = Depends(get_pedido_service),
    estado: Annotated[Optional[str], Query()] = None,
    fecha_desde: Annotated[Optional[date], Query()] = None,
    fecha_hasta: Annotated[Optional[date], Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
) -> PedidoListResponse:
    return service.obtener_pedidos(
        usuario=usuario,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{id}",
    response_model=PedidoDetail,
    status_code=status.HTTP_200_OK,
    summary="Obtener pedido por id",
)
def obtener_pedido_id(
    id: Annotated[int, Path(gt=0)],
    usuario: UserPublic = Depends(get_current_active_user), 
    service: PedidoService = Depends(get_pedido_service),
) -> PedidoDetail:
    return service.obtener_pedido(id, usuario)   


@router.patch(
    "/{id}/avanzar",
    response_model=PedidoDetail,
    status_code=status.HTTP_200_OK,
    summary="Avanzar pedido",
)
def avanzar_pedido(
    id: Annotated[int, Path(gt=0)],
    observacion: Annotated[Optional[str], Body(embed=True)] = None,
    usuario: UserPublic = Depends(get_current_active_user),
    service: PedidoService = Depends(get_pedido_service),
) -> PedidoDetail:
    return service.avanzar_pedido(id, observacion, usuario)   


@router.patch(
    "/{id}/cancelar",
    response_model=PedidoDetail,
    status_code=status.HTTP_200_OK,
    summary="Cancelar pedido",
)
def cancelar_pedido(
    id: Annotated[int, Path(gt=0)],
    observacion: Annotated[Optional[str], Body(embed=True)] = None,
    usuario: UserPublic = Depends(get_current_active_user),
    service: PedidoService = Depends(get_pedido_service),
) -> PedidoDetail:
    return service.cancelar_pedido(id, observacion, usuario)