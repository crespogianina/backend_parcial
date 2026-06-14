from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.database import get_session
from app.core.security import hash_password
from app.main import app
from app.modules.estadisticas.router import get_estadisticas_service
from app.modules.estadisticas.schemas import (
    IngresoFormaPagoItem,
    PedidosEstadoItem,
    ProductoTopItem,
    ResumenResponse,
    VentasPeriodoItem,
)
from app.modules.usuarios.model import Rol, Usuario, UsuarioRol


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine, tables=[Rol.__table__, Usuario.__table__, UsuarioRol.__table__])
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="servicio_mock")
def servicio_mock_fixture():
    mock = MagicMock()
    mock.obtener_resumen.return_value = ResumenResponse(
        ventas_hoy=Decimal("1050.00"),
        ticket_promedio=Decimal("1050.00"),
        pedidos_activos=1,
        ventas_mes_actual=Decimal("1050.00"),
    )
    mock.obtener_ventas_periodo.return_value = [
        VentasPeriodoItem(
            periodo="2026-06-14",
            total_ventas=Decimal("1050.00"),
            cantidad_pedidos=1,
        )
    ]
    mock.obtener_productos_top.return_value = [
        ProductoTopItem(
            producto_id=1,
            nombre="Hamburguesa",
            cantidad_vendida=2,
            ingresos=Decimal("2000.00"),
        )
    ]
    mock.obtener_pedidos_por_estado.return_value = [
        PedidosEstadoItem(estado_codigo="CONFIRMADO", cantidad=1),
        PedidosEstadoItem(estado_codigo="CANCELADO", cantidad=1),
    ]
    mock.obtener_ingresos_por_forma_pago.return_value = [
        IngresoFormaPagoItem(
            forma_pago_codigo="MERCADOPAGO",
            total=Decimal("1050.00"),
            cantidad=1,
        )
    ]
    return mock


@pytest.fixture(name="admin_login")
def admin_login_fixture(session: Session, client: TestClient, servicio_mock):
    app.dependency_overrides[get_estadisticas_service] = lambda: servicio_mock

    session.add(Rol(codigo="ADMIN", nombre="Administrador"))
    session.add(Rol(codigo="CLIENT", nombre="Cliente"))
    session.commit()

    admin = Usuario(
        username="admin",
        nombre="Admin",
        apellido="Test",
        email="admin@test.com",
        password_hash=hash_password("Admin1234!"),
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    session.add(UsuarioRol(usuario_id=admin.id, rol_codigo="ADMIN"))
    session.commit()

    response = client.post(
        "/api/v1/usuario/token",
        data={"username": "admin", "password": "Admin1234!"},
    )
    assert response.status_code == 200
    yield admin
    app.dependency_overrides.pop(get_estadisticas_service, None)


@pytest.fixture(autouse=True)
def limpiar_overrides():
    yield
    app.dependency_overrides.pop(get_estadisticas_service, None)
