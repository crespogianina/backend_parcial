from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.modules.estadisticas.router import get_estadisticas_service
from app.modules.estadisticas.schemas import (
    IngresoFormaPagoItem,
    PedidosEstadoItem,
    ProductoTopItem,
    ResumenResponse,
    VentasPeriodoItem,
)
from app.modules.usuarios.model import Usuario, UsuarioRol
from app.core.security import hash_password

BASE = "/api/v1/estadisticas"


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


@pytest.fixture(autouse=True)
def limpiar_overrides():
    yield
    app.dependency_overrides.pop(get_estadisticas_service, None)


@pytest.fixture(name="admin_login")
def admin_login_fixture(client: TestClient, session: Session, admin_user, servicio_mock):
    app.dependency_overrides[get_estadisticas_service] = lambda: servicio_mock
    res = client.post(
        "/api/v1/usuario/token",
        data={"username": "test_admin", "password": "Admin1234!"},
    )
    assert res.status_code == 200, f"Login admin falló: {res.text}"
    yield admin_user


def test_resumen_ok(client, admin_login):
    response = client.get(f"{BASE}/resumen")
    assert response.status_code == 200
    body = response.json()
    assert body["ventas_hoy"] == "1050.00"
    assert body["pedidos_activos"] == 1


def test_resumen_requiere_admin(client, session):
    response = client.get(f"{BASE}/resumen")
    assert response.status_code == 401


def test_ventas_por_periodo(client, admin_login):
    response = client.get(f"{BASE}/ventas", params={"agrupacion": "day"})
    assert response.status_code == 200
    body = response.json()
    assert body[0]["total_ventas"] == "1050.00"


def test_productos_top(client, admin_login):
    response = client.get(f"{BASE}/productos-top", params={"limit": 5})
    assert response.status_code == 200
    assert response.json()[0]["ingresos"] == "2000.00"


def test_pedidos_por_estado(client, admin_login):
    response = client.get(f"{BASE}/pedidos-por-estado")
    assert response.status_code == 200
    estados = {item["estado_codigo"]: item["cantidad"] for item in response.json()}
    assert estados["CANCELADO"] == 1


def test_ingresos_por_forma_pago(client, admin_login):
    response = client.get(f"{BASE}/ingresos")
    assert response.status_code == 200
    assert response.json()[0]["forma_pago_codigo"] == "MERCADOPAGO"


def test_estadisticas_forbidden_para_cliente(client, session, servicio_mock):
    app.dependency_overrides[get_estadisticas_service] = lambda: servicio_mock

    cliente = Usuario(
        username="juan_stats",
        nombre="Juan",
        apellido="Test",
        email="juan_stats@test.com",
        password_hash=hash_password("Juan1234!"),
    )
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    session.add(UsuarioRol(usuario_id=cliente.id, rol_codigo="CLIENT"))
    session.commit()

    login = client.post(
        "/api/v1/usuario/token",
        data={"username": "juan_stats", "password": "Juan1234!"},
    )
    assert login.status_code == 200

    response = client.get(f"{BASE}/resumen")
    assert response.status_code == 403