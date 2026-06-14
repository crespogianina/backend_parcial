from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.estadisticas.repository import EstadisticasRepository
from app.modules.estadisticas.schemas import (
    AgrupacionVentas,
    IngresoFormaPagoItem,
    PedidosEstadoItem,
    ProductoTopItem,
    ResumenResponse,
    VentasPeriodoItem,
)


class EstadisticasService:
    def __init__(self, session: Session) -> None:
        self._repo = EstadisticasRepository(session)

    def _validar_rango(self, desde: date, hasta: date) -> None:
        if desde > hasta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha 'desde' no puede ser posterior a 'hasta'",
            )

    def _rango_default(self) -> tuple[date, date]:
        hasta = date.today()
        desde = hasta - timedelta(days=30)
        return desde, hasta

    def _formatear_periodo(self, valor: date | object, agrupacion: AgrupacionVentas) -> str:
        if isinstance(valor, date):
            return valor.isoformat()
        if hasattr(valor, "date"):
            return valor.date().isoformat()
        if agrupacion == "month" and hasattr(valor, "strftime"):
            return valor.strftime("%Y-%m")
        if agrupacion == "week" and hasattr(valor, "strftime"):
            return valor.strftime("%Y-W%W")
        return str(valor)[:10]

    def obtener_resumen(self) -> ResumenResponse:
        return ResumenResponse(
            ventas_hoy=self._repo.get_ventas_hoy(),
            ticket_promedio=self._repo.get_ticket_promedio(),
            pedidos_activos=self._repo.get_pedidos_activos(),
            ventas_mes_actual=self._repo.get_ventas_mes_actual(),
        )

    def obtener_ventas_periodo(
        self,
        desde: date | None,
        hasta: date | None,
        agrupacion: AgrupacionVentas,
    ) -> list[VentasPeriodoItem]:
        if desde is None or hasta is None:
            desde, hasta = self._rango_default()
        self._validar_rango(desde, hasta)

        rows = self._repo.get_ventas_periodo(desde, hasta, agrupacion)
        return [
            VentasPeriodoItem(
                periodo=self._formatear_periodo(fila[0], agrupacion),
                total_ventas=fila[1],
                cantidad_pedidos=fila[2],
            )
            for fila in rows
        ]

    def obtener_productos_top(self, limit: int) -> list[ProductoTopItem]:
        rows = self._repo.get_productos_top(limit)
        return [
            ProductoTopItem(
                producto_id=fila[0],
                nombre=fila[1],
                cantidad_vendida=fila[2],
                ingresos=fila[3],
            )
            for fila in rows
        ]

    def obtener_pedidos_por_estado(self) -> list[PedidosEstadoItem]:
        rows = self._repo.get_pedidos_por_estado()
        return [
            PedidosEstadoItem(estado_codigo=fila[0], cantidad=fila[1])
            for fila in rows
        ]

    def obtener_ingresos_por_forma_pago(
        self,
        desde: date | None,
        hasta: date | None,
    ) -> list[IngresoFormaPagoItem]:
        if desde is None or hasta is None:
            desde, hasta = self._rango_default()
        self._validar_rango(desde, hasta)

        rows = self._repo.get_ingresos_por_forma_pago(desde, hasta)
        return [
            IngresoFormaPagoItem(
                forma_pago_codigo=fila[0],
                total=fila[1],
                cantidad=fila[2],
            )
            for fila in rows
        ]
