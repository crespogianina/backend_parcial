from datetime import date
import json
from typing import Optional
from typing_extensions import Annotated
from fastapi import APIRouter, Body, Depends, Path, Query, WebSocket, WebSocketDisconnect, status
from sqlmodel import Session
from app.core.database import get_session, engine
from app.core.deps import get_current_active_user, require_role
from app.modules.pedido.schemas import (
    HistorialEstadoRead,
    PedidoCreate,
    PedidoDetail,
    PedidoListResponse,
)
from app.modules.pedido.service import PedidoService
from app.modules.usuarios.schemas import UserPublic
from app.modules.usuarios.service import UsuarioService
from app.core.websocket import manager

router = APIRouter(prefix="/pedidos", tags=["pedidos"])

COCINA_ROLES = ["cocina", "COCINA", "pedidos", "PEDIDOS", "admin", "ADMIN"]
STAFF_ROLES = ["admin", "pedidos", "cocina"]

# ── Dependencias ──────────────────────────────────────────────────────────────

def get_pedido_service(session: Session = Depends(get_session)) -> PedidoService:
    return PedidoService(session)


def _autenticar_websocket(token: str) -> Optional[tuple[int, str]]:
    with Session(engine) as session:
        return UsuarioService(session).autenticar_websocket(token)


def _pedido_pertenece_a(pedido_id: int, usuario_id: int) -> bool:
    with Session(engine) as session:
        return PedidoService(session).pedido_pertenece_a_usuario(pedido_id, usuario_id)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=PedidoListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar pedidos",
)
def obtener_pedidos(
    usuario: Annotated[UserPublic, Depends(require_role(["ADMIN", "CLIENT", "PEDIDOS"]))],  
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
    usuario: Annotated[UserPublic, Depends(require_role(["ADMIN", "CLIENT"]))], 
    service: PedidoService = Depends(get_pedido_service),
) -> PedidoDetail:
    return service.obtener_pedido(id, usuario)   


@router.post(
    "/",
    response_model=PedidoDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido",
)
def crear_pedido(
    data: PedidoCreate,
    usuario: Annotated[UserPublic, Depends(require_role(["CLIENT"]))], 
    service: PedidoService = Depends(get_pedido_service),
) -> PedidoDetail:
    return service.crear_pedido(usuario.id, data)


@router.patch(
    "/{id}/avanzar",
    response_model=PedidoDetail,
    status_code=status.HTTP_200_OK,
    summary="Avanzar pedido",
)
async def avanzar_pedido(
    id: Annotated[int, Path(gt=0)],
    usuario: Annotated[UserPublic, Depends(require_role(["ADMIN", "PEDIDOS"]))], 
    observacion: Annotated[Optional[str], Body(embed=True)] = None,
    service: PedidoService = Depends(get_pedido_service),
) -> PedidoDetail:
    return await service.avanzar_pedido(id, observacion, usuario)   


@router.patch(
    "/{id}/cancelar",
    response_model=PedidoDetail,
    status_code=status.HTTP_200_OK,
    summary="Cancelar pedido",
)
def cancelar_pedido(
    id: Annotated[int, Path(gt=0)],
    usuario: Annotated[UserPublic, Depends(require_role(["ADMIN", "PEDIDOS"]))], 
    observacion: Annotated[Optional[str], Body(embed=True)] = None,
    service: PedidoService = Depends(get_pedido_service),
) -> PedidoDetail:
    return service.cancelar_pedido(id, observacion, usuario)

@router.get(
    "/{id}/historial",
    response_model=list[HistorialEstadoRead],
    status_code=status.HTTP_200_OK,
    summary="Obtener historial de estados del pedido",
)
def obtener_historial_pedido(
    id: Annotated[int, Path(gt=0)],
    usuario: Annotated[UserPublic, Depends(get_current_active_user)],
    service: PedidoService = Depends(get_pedido_service),
) -> list[HistorialEstadoRead]:
    return service.obtener_historial_pedido(id, usuario)


@router.delete(
    "/{id}",
    response_model=PedidoDetail,
    status_code=status.HTTP_200_OK,
    summary="Cancelar pedido propio (CLIENT, solo PENDIENTE o CONFIRMADO)",
)
def cancelar_pedido_propio(
    id: Annotated[int, Path(gt=0)],
    usuario: Annotated[UserPublic, Depends(require_role(["CLIENT"]))],
    service: PedidoService = Depends(get_pedido_service),
    motivo: Annotated[Optional[str], Query(max_length=200)] = None,
) -> PedidoDetail:
    return service.cancelar_pedido_propio(id, usuario, motivo)


@router.websocket("/ws")
async def pedidos_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token") or websocket.cookies.get("access_token")

    if not token:
        await websocket.accept()
        await websocket.close(code=1008, reason="Token requerido")
        return

    auth = _autenticar_websocket(token)

    if not auth:
        await websocket.accept()
        await websocket.close(code=1008, reason="Token inválido o usuario inactivo")
        return

    user_id, user_role = auth

    await manager.connect(websocket, role=user_role, user_id=user_id)
    es_staff = user_role.upper() in STAFF_ROLES

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            action = msg.get("action")
            order_id = msg.get("order_id")

            if action == "subscribe-order" and isinstance(order_id, int):

                if not es_staff and not _pedido_pertenece_a(order_id, user_id):
                    await websocket.send_json({
                        "event": "ERROR",
                        "data": {"detail": "No autorizado para este pedido"},
                    })
                    continue

                manager.join_order_room(websocket, order_id)
                await websocket.send_json({
                    "event": "SUBSCRIBED",
                    "data": {"order_id": order_id},
                })

            elif action == "unsubscribe-order" and isinstance(order_id, int):
                manager.leave_order_room(websocket, order_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)