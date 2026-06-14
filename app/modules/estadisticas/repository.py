from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, cast, func
from sqlmodel import Session, select

from app.modules.estadisticas.schemas import AgrupacionVentas
from app.modules.pago.models import Pago
from app.modules.pedido.models import DetallePedido, EstadoPedido, Pedido

ESTADO_CANCELADO = "CANCELADO"
MP_APROBADO = "approved"


class EstadisticasRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _filtro_fecha_pedido(
        self,
        statement,
        desde: Optional[date],
        hasta: Optional[date],
    ):
        if desde is not None:
            statement = statement.where(cast(Pedido.created_at, Date) >= desde)
        if hasta is not None:
            statement = statement.where(cast(Pedido.created_at, Date) <= hasta)
        return statement

    def _excluir_cancelados(self, statement):
        return statement.where(Pedido.estado_codigo != ESTADO_CANCELADO)

    def get_ventas_hoy(self) -> Decimal:
        hoy = datetime.now(timezone.utc).date()
        statement = (
            select(func.coalesce(func.sum(Pedido.total), 0))
            .select_from(Pedido)
            .where(
                Pedido.estado_codigo != ESTADO_CANCELADO,
                cast(Pedido.created_at, Date) == hoy,
            )
        )
        return Decimal(str(self.session.exec(statement).one()))

    def get_ventas_mes_actual(self) -> Decimal:
        ahora = datetime.now(timezone.utc)
        inicio_mes = ahora.replace(day=1).date()
        statement = (
            select(func.coalesce(func.sum(Pedido.total), 0))
            .select_from(Pedido)
            .where(
                Pedido.estado_codigo != ESTADO_CANCELADO,
                cast(Pedido.created_at, Date) >= inicio_mes,
            )
        )
        return Decimal(str(self.session.exec(statement).one()))

    def get_ticket_promedio(self) -> Decimal:
        statement = (
            select(func.coalesce(func.avg(Pedido.total), 0))
            .select_from(Pedido)
            .where(Pedido.estado_codigo != ESTADO_CANCELADO)
        )
        return Decimal(str(self.session.exec(statement).one())).quantize(Decimal("0.01"))

    def get_pedidos_activos(self) -> int:
        statement = (
            select(func.count())
            .select_from(Pedido)
            .join(EstadoPedido, Pedido.estado_codigo == EstadoPedido.codigo)
            .where(EstadoPedido.es_terminal.is_(False))
        )
        return int(self.session.exec(statement).one())

    def get_ventas_periodo(
        self,
        desde: date,
        hasta: date,
        agrupacion: AgrupacionVentas,
    ) -> list[tuple[datetime, Decimal, int]]:
        if agrupacion == "day":
            periodo_expr = cast(Pedido.created_at, Date)
        else:
            periodo_expr = func.date_trunc(agrupacion, Pedido.created_at)

        statement = (
            select(
                periodo_expr,
                func.coalesce(func.sum(Pedido.total), 0),
                func.count(Pedido.id),
            )
            .select_from(Pedido)
            .where(
                Pedido.estado_codigo != ESTADO_CANCELADO,
                cast(Pedido.created_at, Date) >= desde,
                cast(Pedido.created_at, Date) <= hasta,
            )
            .group_by(periodo_expr)
            .order_by(periodo_expr)
        )
        rows = self.session.exec(statement).all()
        return [(row[0], Decimal(str(row[1])), int(row[2])) for row in rows]

    def get_productos_top(self, limit: int) -> list[tuple[int, str, int, Decimal]]:
        statement = (
            select(
                DetallePedido.producto_id,
                DetallePedido.nombre_snapshot,
                func.coalesce(func.sum(DetallePedido.cantidad), 0),
                func.coalesce(func.sum(DetallePedido.subtotal_snap), 0),
            )
            .join(Pedido, DetallePedido.pedido_id == Pedido.id)
            .where(Pedido.estado_codigo != ESTADO_CANCELADO)
            .group_by(DetallePedido.producto_id, DetallePedido.nombre_snapshot)
            .order_by(func.sum(DetallePedido.subtotal_snap).desc())
            .limit(limit)
        )
        rows = self.session.exec(statement).all()
        return [
            (int(row[0]), row[1], int(row[2]), Decimal(str(row[3])))
            for row in rows
        ]

    def get_pedidos_por_estado(self) -> list[tuple[str, int]]:
        statement = (
            select(Pedido.estado_codigo, func.count(Pedido.id))
            .select_from(Pedido)
            .group_by(Pedido.estado_codigo)
            .order_by(Pedido.estado_codigo)
        )
        rows = self.session.exec(statement).all()
        return [(row[0], int(row[1])) for row in rows]

    def get_ingresos_por_forma_pago(
        self,
        desde: date,
        hasta: date,
    ) -> list[tuple[str, Decimal, int]]:
        statement = (
            select(
                Pedido.forma_pago_codigo,
                func.coalesce(func.sum(Pago.transaction_amount), 0),
                func.count(Pago.id),
            )
            .join(Pago, Pago.pedido_id == Pedido.id)
            .where(
                Pago.mp_status == MP_APROBADO,
                Pedido.estado_codigo != ESTADO_CANCELADO,
                cast(Pedido.created_at, Date) >= desde,
                cast(Pedido.created_at, Date) <= hasta,
            )
            .group_by(Pedido.forma_pago_codigo)
            .order_by(func.sum(Pago.transaction_amount).desc())
        )
        rows = self.session.exec(statement).all()
        return [(row[0], Decimal(str(row[1])), int(row[2])) for row in rows]
