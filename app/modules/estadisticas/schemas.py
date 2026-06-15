from decimal import Decimal
from typing import Literal

from sqlmodel import SQLModel


class ResumenResponse(SQLModel):
    ventas_hoy: Decimal
    ticket_promedio: Decimal
    pedidos_activos: int
    ventas_mes_actual: Decimal


class VentasPeriodoItem(SQLModel):
    periodo: str
    total_ventas: Decimal
    cantidad_pedidos: int


class ProductoTopItem(SQLModel):
    producto_id: int
    nombre: str
    cantidad_vendida: int
    ingresos: Decimal


class PedidosEstadoItem(SQLModel):
    estado_codigo: str
    cantidad: int


class IngresoFormaPagoItem(SQLModel):
    forma_pago_codigo: str
    total: Decimal
    cantidad: int


AgrupacionVentas = Literal["day", "week", "month"]
