# from datetime import datetime
# from typing import Optional

# from sqlalchemy import BigInteger, CHAR, Numeric, ForeignKey, String
# from sqlmodel import SQLModel, Field, Relationship
# from sqlalchemy import Column, PrimaryKeyConstraint


# class Rol(SQLModel, table=True):
#     __tablename__ = "roles"

#     codigo: str = Field(max_length=20, primary_key=True)
#     nombre: str = Field(unique=True, nullable=False, max_length=50)
#     descripcion: Optional[str] = Field(default=None)

#     usuario_roles: list["UsuarioRol"] = Relationship(back_populates="rol")


# class Usuario(SQLModel, table=True):
#     __tablename__ = "usuarios"

#     id: Optional[int] = Field( default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))

#     nombre: str = Field(nullable=False, max_length=80)
#     apellido: str = Field(nullable=False, max_length=80)
#     username: str = Field(unique=True, nullable=False, max_length=80)
#     email: str = Field(unique=True, nullable=False, max_length=254)
#     celular: Optional[str] = Field(default=None, max_length=20)
#     password_hash: str = Field(sa_column=Column(CHAR(60), nullable=False))

#     created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
#     updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
#     deleted_at: Optional[datetime] = Field(default=None)

#     direcciones: list["DireccionEntrega"] = Relationship(back_populates="usuario")
#     refresh_tokens: list["RefreshToken"] = Relationship(back_populates="usuario")

#     usuario_roles: list["UsuarioRol"] = Relationship(
#         back_populates="usuario",
#         sa_relationship_kwargs={
#             "primaryjoin": "Usuario.id == foreign(UsuarioRol.usuario_id)",
#             "foreign_keys": "[UsuarioRol.usuario_id]",
#         }
#     )


# class DireccionEntrega(SQLModel, table=True):
#     __tablename__ = "direcciones_entrega"

#     id: Optional[int] = Field( default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))

#     usuario_id: int = Field(sa_column=Column(BigInteger, ForeignKey("usuarios.id"), nullable=False))

#     alias: Optional[str] = Field(default=None, max_length=50)
#     linea1: str = Field(nullable=False)
#     linea2: Optional[str] = Field(default=None)
#     ciudad: str = Field(nullable=False, max_length=100)
#     provincia: Optional[str] = Field(default=None, max_length=100)
#     codigo_postal: Optional[str] = Field(default=None, max_length=10)

#     latitud: Optional[float] = Field( default=None, sa_column=Column(Numeric(9, 6)))
#     longitud: Optional[float] = Field( default=None, sa_column=Column(Numeric(9, 6)))

#     es_principal: bool = Field(default=False, nullable=False)

#     created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
#     updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
#     deleted_at: Optional[datetime] = Field(default=None)

#     usuario: Optional["Usuario"] = Relationship(back_populates="direcciones")


# class UsuarioRol(SQLModel, table=True):
#     __tablename__ = "usuario_rol"

#     __table_args__ = (PrimaryKeyConstraint("usuario_id", "rol_codigo"),)

#     usuario_id: int = Field(sa_column=Column(BigInteger, ForeignKey("usuarios.id"), nullable=False))
#     rol_codigo: str = Field(sa_column=Column(String(20), ForeignKey("roles.codigo"), nullable=False))

#     asignado_por_id: Optional[int] = Field( default=None, sa_column=Column(BigInteger, ForeignKey("usuarios.id")))
#     expires_at: Optional[datetime] = Field(default=None)

#     created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

#     usuario: Optional["Usuario"] = Relationship(
#         back_populates="usuario_roles",
#         sa_relationship_kwargs={"foreign_keys": lambda: [UsuarioRol.usuario_id]}
#     )
#     rol: Optional["Rol"] = Relationship(back_populates="usuario_roles")


# class RefreshToken(SQLModel, table=True):
#     __tablename__ = "refresh_tokens"

#     id: Optional[int] = Field( default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))

#     usuario_id: int = Field(sa_column=Column(BigInteger, ForeignKey("usuarios.id"), nullable=False))

#     token_hash: str = Field(sa_column=Column(CHAR(64), unique=True, nullable=False))
#     expires_at: datetime = Field(nullable=False)
#     revoked_at: Optional[datetime] = Field(default=None)

#     created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

#     usuario: Optional["Usuario"] = Relationship(back_populates="refresh_tokens")


from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import BigInteger, CHAR, Numeric, ForeignKey, String, Text, Index
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, PrimaryKeyConstraint


class Rol(SQLModel, table=True):
    __tablename__ = "roles"

    codigo: str = Field(max_length=20, primary_key=True)
    nombre: str = Field(unique=True, nullable=False, max_length=50)
    descripcion: Optional[str] = Field(default=None, sa_column=Column(Text))

    usuario_roles: list["UsuarioRol"] = Relationship(back_populates="rol")


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )

    nombre: str = Field(nullable=False, max_length=80)
    apellido: str = Field(nullable=False, max_length=80)
    username: str = Field(unique=True, nullable=False, max_length=80)
    email: str = Field(unique=True, nullable=False, max_length=254)
    celular: Optional[str] = Field(default=None, max_length=20)
    password_hash: str = Field(sa_column=Column(CHAR(60), nullable=False))

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    deleted_at: Optional[datetime] = Field(default=None)

    direcciones: list["DireccionEntrega"] = Relationship(back_populates="usuario")

    usuario_roles: list["UsuarioRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={
            "primaryjoin": "Usuario.id == foreign(UsuarioRol.usuario_id)",
            "foreign_keys": "[UsuarioRol.usuario_id]",
        }
    )


class DireccionEntrega(SQLModel, table=True):
    __tablename__ = "direcciones_entrega"

    __table_args__ = (
        Index("ix_direcciones_entrega_usuario_id", "usuario_id"),
    )

    id: Optional[int] = Field( default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))

    usuario_id: int = Field(sa_column=Column(BigInteger, ForeignKey("usuarios.id"), nullable=False))

    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: str = Field(nullable=False)
    linea2: Optional[str] = Field(default=None)
    ciudad: str = Field(nullable=False, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)

    latitud: Optional[float] = Field(default=None, sa_column=Column(Numeric(9, 6)))
    longitud: Optional[float] = Field(default=None, sa_column=Column(Numeric(9, 6)))

    es_principal: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    deleted_at: Optional[datetime] = Field(default=None)

    usuario: Optional["Usuario"] = Relationship(back_populates="direcciones")


class UsuarioRol(SQLModel, table=True):
    __tablename__ = "usuario_rol"

    __table_args__ = (PrimaryKeyConstraint("usuario_id", "rol_codigo"),)

    usuario_id: int = Field(sa_column=Column(BigInteger, ForeignKey("usuarios.id"), nullable=False))
    rol_codigo: str = Field(sa_column=Column(String(20), ForeignKey("roles.codigo"), nullable=False))

    asignado_por_id: Optional[int] = Field( default=None, sa_column=Column(BigInteger, ForeignKey("usuarios.id")))
    expires_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

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