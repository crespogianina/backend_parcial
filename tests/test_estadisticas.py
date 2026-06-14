from app.core.security import hash_password
from app.main import app
from app.modules.estadisticas.router import get_estadisticas_service
from app.modules.usuarios.model import Rol, Usuario, UsuarioRol


def test_resumen_ok(client, admin_login):
    response = client.get("/api/v1/estadisticas/resumen")
    assert response.status_code == 200
    body = response.json()
    assert body["ventas_hoy"] == "1050.00"
    assert body["pedidos_activos"] == 1


def test_resumen_requiere_admin(client, session):
    response = client.get("/api/v1/estadisticas/resumen")
    assert response.status_code == 401


def test_ventas_por_periodo(client, admin_login):
    response = client.get(
        "/api/v1/estadisticas/ventas",
        params={"agrupacion": "day"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body[0]["total_ventas"] == "1050.00"


def test_productos_top(client, admin_login):
    response = client.get("/api/v1/estadisticas/productos-top", params={"limit": 5})
    assert response.status_code == 200
    assert response.json()[0]["ingresos"] == "2000.00"


def test_pedidos_por_estado(client, admin_login):
    response = client.get("/api/v1/estadisticas/pedidos-por-estado")
    assert response.status_code == 200
    estados = {item["estado_codigo"]: item["cantidad"] for item in response.json()}
    assert estados["CANCELADO"] == 1


def test_ingresos_por_forma_pago(client, admin_login):
    response = client.get("/api/v1/estadisticas/ingresos")
    assert response.status_code == 200
    assert response.json()[0]["forma_pago_codigo"] == "MERCADOPAGO"


def test_estadisticas_forbidden_para_cliente(client, session, servicio_mock):
    app.dependency_overrides[get_estadisticas_service] = lambda: servicio_mock

    session.add(Rol(codigo="CLIENT", nombre="Cliente"))
    session.commit()

    cliente = Usuario(
        username="juan",
        nombre="Juan",
        apellido="Test",
        email="juan@test.com",
        password_hash=hash_password("Juan1234!"),
    )
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    session.add(UsuarioRol(usuario_id=cliente.id, rol_codigo="CLIENT"))
    session.commit()

    login = client.post(
        "/api/v1/usuario/token",
        data={"username": "juan", "password": "Juan1234!"},
    )
    assert login.status_code == 200

    response = client.get("/api/v1/estadisticas/resumen")
    assert response.status_code == 403
