
from datetime import datetime
from decimal import Decimal
from typing import Optional, Text
from pydantic import Field
from sqlalchemy import BigInteger, Column, ForeignKey, Numeric, String
from sqlmodel import PrimaryKeyConstraint, SQLModel


class EstadoPedido(SQLModel, table=True):
    __tablename__ = "estados_pedido"

    codigo: str = Field(max_length=20, primary_key=True)
    
    descripcion: str = Field(nullable=False, max_length=80)
    orden: int = Field(nullable=False)
    es_terminal: bool = Field(nullable=False)


class DetallePedido(SQLModel, table=True):
    __tablename__ = "detalles_pedido"

    __table_args__ = (PrimaryKeyConstraint("pedido_id", "producto_id"),)

    pedido_id: int = Field(sa_column=Column(BigInteger, ForeignKey("pedidos.id"), nullable=False))
    producto_id: int = Field(sa_column=Column(BigInteger, ForeignKey("productos.id"), nullable=False))
    
    cantidad: int = Field(nullable=False)

    nombre_snapshot: str = Field(nullable=False, max_length=200)
    pecio_snapshot: float = Field(nullable=False, sa_column=Column(Numeric(10, 2)))
    subtotal_snap: float = Field(nullable=False, sa_column=Column(Numeric(10, 2)))
    personalizacion: int = Field(max_length=200) #consultar
    
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
   

class HistorialPedido(SQLModel, table=True):
    __tablename__ = "historial_pedido"

    id: str = Field(max_length=20, primary_key=True)

    pedido_id: int = Field(sa_column=Column(BigInteger, ForeignKey("pedidos.id"), nullable=False))
    estado_desde: str = Field(sa_column=Column(Numeric(10, 2), ForeignKey("estados_pedido.codigo"), nullable=False))
    estado_hacia: str = Field(sa_column=Column(Numeric(10, 2), ForeignKey("estados_pedido.codigo"), nullable=False))
    usuario_id: int = Field(sa_column=Column(String(20), ForeignKey("estados_pedido.codigo"), nullable=False))

    motivo: str = Field(default=None)
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False)



class Pedido(SQLModel, table=True):
    __tablename__ = "pedidos"

    id: Optional[int] = Field( default=None, primary_key=True, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))

    usuario_id: int = Field(sa_column=Column( BigInteger, ForeignKey("usuarios.id"), nullable=False))
    direccion_id: Optional[int] = Field( default=None, sa_column=Column( BigInteger, ForeignKey("direcciones_entrega.id"), nullable=True))
    estado_codigo: str = Field(sa_column=Column( String(20), ForeignKey("estados_pedido.codigo"), nullable=False))
    forma_pago_codigo: str = Field(sa_column=Column( String(20), ForeignKey("formas_pago.codigo"), nullable=False))
    
    subtotal: Decimal = Field(sa_column=Column( Numeric(10, 2), nullable=False))
    descuento: Decimal = Field(default=Decimal("0.00"), sa_column=Column( Numeric(10, 2), nullable=False, default=0.00))
    costo_envio: Decimal = Field(default=Decimal("50.00"), sa_column=Column( Numeric(10, 2), nullable=False, default=50.00))
    total: Decimal = Field(sa_column=Column( Numeric(10, 2), nullable=False))

    notas: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    deleted_at: Optional[datetime] = Field(default=None) 



class FormaPago(SQLModel, table=True):
    __tablename__ = "formas_pago"

    codigo: str = Field(max_length=20, primary_key=True)
    
    descripcion: str = Field(nullable=False, max_length=80)
    habilitado: bool = Field(nullable=False, default=True) 


# class Pago(SQLModel, table=True):
#     __tablename__ = "pagos"

#     id: int = Field(primary_key=True)

#     pedido_id: int = Field(sa_column=Column( BigInteger, ForeignKey("pedidos.id"), nullable=False))
    
