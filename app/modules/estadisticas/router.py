from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_role
from app.modules.estadisticas.schemas import (
    AgrupacionVentas,
    IngresoFormaPagoItem,
    PedidosEstadoItem,
    ProductoTopItem,
    ResumenResponse,
    VentasPeriodoItem,
)
from app.modules.estadisticas.service import EstadisticasService
from app.modules.usuarios.schemas import UserPublic

router = APIRouter()


def get_estadisticas_service(session: Session = Depends(get_session)) -> EstadisticasService:
    return EstadisticasService(session)


@router.get(
    "/resumen",
    response_model=ResumenResponse,
    status_code=status.HTTP_200_OK,
    summary="KPIs generales del negocio",
)
def obtener_resumen(
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    service: EstadisticasService = Depends(get_estadisticas_service),
) -> ResumenResponse:
    return service.obtener_resumen()


@router.get(
    "/ventas",
    response_model=list[VentasPeriodoItem],
    status_code=status.HTTP_200_OK,
    summary="Ventas agrupadas por período",
)
def obtener_ventas_periodo(
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    service: EstadisticasService = Depends(get_estadisticas_service),
    desde: Annotated[Optional[date], Query()] = None,
    hasta: Annotated[Optional[date], Query()] = None,
    agrupacion: Annotated[AgrupacionVentas, Query()] = "day",
) -> list[VentasPeriodoItem]:
    return service.obtener_ventas_periodo(desde, hasta, agrupacion)


@router.get(
    "/productos-top",
    response_model=list[ProductoTopItem],
    status_code=status.HTTP_200_OK,
    summary="Productos con mayor facturación",
)
def obtener_productos_top(
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    service: EstadisticasService = Depends(get_estadisticas_service),
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[ProductoTopItem]:
    return service.obtener_productos_top(limit)


@router.get(
    "/pedidos-por-estado",
    response_model=list[PedidosEstadoItem],
    status_code=status.HTTP_200_OK,
    summary="Cantidad de pedidos por estado actual",
)
def obtener_pedidos_por_estado(
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    service: EstadisticasService = Depends(get_estadisticas_service),
) -> list[PedidosEstadoItem]:
    return service.obtener_pedidos_por_estado()


@router.get(
    "/ingresos",
    response_model=list[IngresoFormaPagoItem],
    status_code=status.HTTP_200_OK,
    summary="Ingresos confirmados por forma de pago",
)
def obtener_ingresos(
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    service: EstadisticasService = Depends(get_estadisticas_service),
    desde: Annotated[Optional[date], Query()] = None,
    hasta: Annotated[Optional[date], Query()] = None,
) -> list[IngresoFormaPagoItem]:
    return service.obtener_ingresos_por_forma_pago(desde, hasta)
