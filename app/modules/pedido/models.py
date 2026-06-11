
from datetime import timezone, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ARRAY, BigInteger, Column, ForeignKey, Integer, Numeric, PrimaryKeyConstraint, String, Boolean, Text
from sqlmodel import Relationship, SQLModel, Field


if TYPE_CHECKING:
    from app.modules.pago.models import Pago
    from app.modules.direcciones.model import DireccionEntrega
    from app.modules.producto.models import Producto
    from app.modules.usuarios.model import Usuario

class EstadoPedido(SQLModel, table=True):
    __tablename__ = "estado_pedido"

    codigo: str = Field(sa_column=Column(String(20), primary_key=True))

    descripcion: str = Field(sa_column=Column(String(80), nullable=False))
    orden: int = Field(sa_column=Column(Integer, nullable=False))
    es_terminal: bool = Field(sa_column=Column(Boolean, nullable=False))

    pedidos: List["Pedido"] = Relationship(
        back_populates="estado",
        sa_relationship_kwargs={ "foreign_keys": "[Pedido.estado_codigo]", "lazy": "selectin"}
    )
    historial_estado_desde: List["HistorialEstadoPedido"] = Relationship(
        back_populates="estado_desde_rel",
        sa_relationship_kwargs={ "foreign_keys": "[HistorialEstadoPedido.estado_desde]", "lazy": "selectin"}
    )
    historial_estado_hacia: List["HistorialEstadoPedido"] = Relationship(
        back_populates="estado_hacia_rel",
        sa_relationship_kwargs={ "foreign_keys": "[HistorialEstadoPedido.estado_hacia]", "lazy": "selectin"}
    )


class FormaPago(SQLModel, table=True):
    __tablename__ = "formas_pago"

    codigo: str = Field(sa_column=Column(String(20), primary_key=True))

    descripcion: str = Field(sa_column=Column(String(80), nullable=False))
    habilitado: bool = Field(sa_column=Column(Boolean, nullable=False, default=True))

    pedidos: List["Pedido"] = Relationship(
        back_populates="forma_pago",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Pedido(SQLModel, table=True):
    __tablename__ = "pedidos"

    id: Optional[int] = Field(default=None, primary_key=True)

    usuario_id: int = Field(sa_column=Column(BigInteger, ForeignKey("usuarios.id"), nullable=False))
    direccion_id: Optional[int] = Field(default=None, sa_column=Column( BigInteger, ForeignKey("direcciones_entrega.id"), nullable=True))
    estado_codigo: str = Field(sa_column=Column(String(20), ForeignKey("estado_pedido.codigo"), nullable=False))
    forma_pago_codigo: str = Field(sa_column=Column(String(20), ForeignKey("formas_pago.codigo"), nullable=False))
    
    subtotal: Decimal = Field(sa_column=Column( Numeric(10, 2), nullable=False))
    descuento: Decimal = Field(default=Decimal("0.00"), sa_column=Column( Numeric(10, 2), nullable=False, default=0.00))
    costo_envio: Decimal = Field(default=Decimal("50.00"), sa_column=Column( Numeric(10, 2), nullable=False, default=50.00))
    total: Decimal = Field(sa_column=Column( Numeric(10, 2), nullable=False))

    notas: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at: Optional[datetime] = Field(default=None) 

    usuario: Optional["Usuario"] = Relationship(
        back_populates="pedidos",
        sa_relationship_kwargs={"foreign_keys": "[Pedido.usuario_id]", "lazy": "selectin"}
    )
    direccion: Optional["DireccionEntrega"] = Relationship(
        back_populates="pedidos",
        sa_relationship_kwargs={"foreign_keys": "[Pedido.direccion_id]", "lazy": "selectin"}
    )
    estado: Optional["EstadoPedido"] = Relationship(
        back_populates="pedidos",
        sa_relationship_kwargs={ "foreign_keys": "[Pedido.estado_codigo]", "lazy": "selectin"}
    )
    forma_pago: Optional["FormaPago"] = Relationship(
        back_populates="pedidos",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    detalles: List["DetallePedido"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={ "cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    historial: List["HistorialEstadoPedido"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={ "cascade": "all, delete-orphan", "order_by": "HistorialEstadoPedido.created_at", "lazy": "selectin"}
    )
    #pagos: List["Pago"] = Relationship(back_populates="pedido")

class DetallePedido(SQLModel, table=True):
    __tablename__ = "detalles_pedido"

    __table_args__ = (PrimaryKeyConstraint("pedido_id", "producto_id"),)

    pedido_id: int = Field(sa_column=Column(BigInteger, ForeignKey("pedidos.id"), nullable=False))
    producto_id: int = Field(sa_column=Column(BigInteger, ForeignKey("productos.id"), nullable=False))
    
    cantidad: int = Field(sa_column=Column(Integer, nullable=False))

    nombre_snapshot: str = Field(sa_column=Column(String(200), nullable=False))
    precio_snapshot: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    subtotal_snap: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    personalizacion: Optional[list[int]] = Field(default=None, sa_column=Column(ARRAY(Integer), nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
   
    pedido: Optional["Pedido"] = Relationship(
        back_populates="detalles",
        sa_relationship_kwargs={"foreign_keys": "[DetallePedido.pedido_id]"}
    )
    producto: Optional["Producto"] = Relationship(
        back_populates="detalles_pedido",
        sa_relationship_kwargs={"foreign_keys": "[DetallePedido.producto_id]", "lazy": "joined"}
    )


class HistorialEstadoPedido(SQLModel, table=True):
    __tablename__ = "historial_estado_pedido"

    id: Optional[int] = Field(default=None,sa_column=Column(BigInteger, primary_key=True, autoincrement=True))

    pedido_id: int = Field(sa_column=Column(BigInteger, ForeignKey("pedidos.id"), nullable=False))
    estado_desde: Optional[str] = Field(sa_column=Column(String(20), ForeignKey("estado_pedido.codigo"), nullable=True))
    estado_hacia: str = Field(sa_column=Column(String(20), ForeignKey("estado_pedido.codigo"), nullable=False))

    usuario_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, ForeignKey("usuarios.id"), nullable=True),
    )

    motivo: Optional[str] = Field( default=None, sa_column=Column(Text, nullable=True))
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)

    pedido: Optional["Pedido"] = Relationship(
        back_populates="historial",
        sa_relationship_kwargs={"foreign_keys": "[HistorialEstadoPedido.pedido_id]"}
    )
    estado_desde_rel: Optional["EstadoPedido"] = Relationship(
        back_populates="historial_estado_desde",
        sa_relationship_kwargs={ "foreign_keys": "[HistorialEstadoPedido.estado_desde]", "lazy": "joined"}
    )
    estado_hacia_rel: "EstadoPedido" = Relationship(
        back_populates="historial_estado_hacia",
        sa_relationship_kwargs={
            "foreign_keys": "[HistorialEstadoPedido.estado_hacia]","lazy": "joined"}
    )
    usuario: Optional["Usuario"] = Relationship(
        back_populates="historial_pedidos",
        sa_relationship_kwargs={ "foreign_keys": "[HistorialEstadoPedido.usuario_id]", "lazy": "joined"}
    )