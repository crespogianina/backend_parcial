from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, CHAR, ForeignKey, String, Text
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, PrimaryKeyConstraint
from app.modules.direcciones.model import DireccionEntrega

if TYPE_CHECKING:
    from app.modules.pedido.models import Pedido, HistorialEstadoPedido

class Rol(SQLModel, table=True):
    __tablename__ = "roles"

    codigo: str = Field(max_length=20, primary_key=True)
    nombre: str = Field(unique=True, nullable=False, max_length=50)
    descripcion: Optional[str] = Field(default=None, sa_column=Column(Text))

    usuario_roles: list["UsuarioRol"] = Relationship(back_populates="rol")


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    id: Optional[int] = Field(default=None, primary_key=True)

    nombre: str = Field(nullable=False, max_length=80)
    apellido: str = Field(nullable=False, max_length=80)
    username: str = Field(unique=True, nullable=False, max_length=80)
    email: str = Field(unique=True, nullable=False, max_length=254)
    celular: Optional[str] = Field(default=None, max_length=20)
    password_hash: str = Field(sa_column=Column(CHAR(60), nullable=False))

    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at: Optional[datetime] = Field(default=None)

    direcciones: list["DireccionEntrega"] = Relationship(back_populates="usuario")
    usuario_roles: list["UsuarioRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={
            "primaryjoin": "Usuario.id == foreign(UsuarioRol.usuario_id)",
            "foreign_keys": "[UsuarioRol.usuario_id]",
        }
    )
    pedidos: list["Pedido"] = Relationship(back_populates="usuario") 
    historial_pedidos: list["HistorialEstadoPedido"] = Relationship(back_populates="usuario") 


class UsuarioRol(SQLModel, table=True):
    __tablename__ = "usuario_rol"

    __table_args__ = (PrimaryKeyConstraint("usuario_id", "rol_codigo"),)

    usuario_id: int = Field(sa_column=Column(BigInteger, ForeignKey("usuarios.id"), nullable=False))
    rol_codigo: str = Field(sa_column=Column(String(20), ForeignKey("roles.codigo"), nullable=False))

    asignado_por_id: Optional[int] = Field( default=None, sa_column=Column(BigInteger, ForeignKey("usuarios.id")))
    expires_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    usuario: Optional["Usuario"] = Relationship(
        back_populates="usuario_roles",
        sa_relationship_kwargs={
            "foreign_keys": "[UsuarioRol.usuario_id]",
        }
    )
    asignado_por: Optional["Usuario"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[UsuarioRol.asignado_por_id]",
            "primaryjoin": "UsuarioRol.asignado_por_id == Usuario.id",
        }
    )

    rol: Optional["Rol"] = Relationship(back_populates="usuario_roles")