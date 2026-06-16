import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.pedido.models import Pedido, DetallePedido, HistorialEstadoPedido
from tests.conftest import set_auth_cookie, clear_auth_cookie

BASE = "/api/v1/pagos"
BASE_PED = "/api/v1/pedidos"


@pytest.fixture(name="client_user_2")
def client_user_2_fixture(session: Session):
    from app.modules.usuarios.model import Usuario, UsuarioRol
    from app.core.security import hash_password
    user = Usuario(
        username="test_client_pago_2",
        nombre="Test",
        apellido="Client2",
        email="client_pago_2@test.com",
        password_hash=hash_password("Client1234!"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UsuarioRol(usuario_id=user.id, rol_codigo="CLIENT"))
    session.commit()
    uid = user.id
    session.expunge(user)
    user.id = uid
    return user


@pytest.fixture(name="direccion_client")
def direccion_client_fixture(client: TestClient, session: Session, client_user):
    set_auth_cookie(client, session, client_user)
    res = client.post("/api/v1/direcciones", json={
        "alias": "Casa pago",
        "linea1": "Av. Corrientes 1234",
        "ciudad": "Buenos Aires",
        "provincia": "Buenos Aires",
        "codigo_postal": "1043",
        "es_principal": True,
    })
    clear_auth_cookie(client)
    assert res.status_code == 201
    return res.json()["id"]


@pytest.fixture(name="pedido_mp_pendiente")
def pedido_mp_pendiente_fixture(session: Session, client_user, producto_final, seed_estados_pedido, seed_formas_pago, direccion_client):
    pedido = Pedido(
        usuario_id=client_user.id,
        estado_codigo="PENDIENTE",
        forma_pago_codigo="MERCADOPAGO",
        subtotal=1000.0,
        descuento=0.0,
        costo_envio=500.0,
        total=1500.0,
        direccion_id=direccion_client,
    )
    session.add(pedido)
    session.commit()
    session.refresh(pedido)
    session.add(DetallePedido(
        pedido_id=pedido.id,
        producto_id=producto_final.id,
        nombre_snapshot="Producto Final Test",
        cantidad=1,
        precio_snapshot=1000.0,
        subtotal_snap=1000.0,
    ))
    session.add(HistorialEstadoPedido(
        pedido_id=pedido.id,
        estado_desde=None,
        estado_hacia="PENDIENTE",
        usuario_id=client_user.id,
        motivo="Pedido creado",
    ))
    session.commit()
    pid = pedido.id
    session.expunge(pedido)
    pedido.id = pid
    return pedido


@pytest.fixture(name="pedido_efectivo_pendiente")
def pedido_efectivo_pendiente_fixture(session: Session, client_user, producto_final, seed_estados_pedido, seed_formas_pago):
    pedido = Pedido(
        usuario_id=client_user.id,
        estado_codigo="PENDIENTE",
        forma_pago_codigo="EFECTIVO",
        subtotal=1000.0,
        descuento=0.0,
        costo_envio=0.0,
        total=1000.0,
    )
    session.add(pedido)
    session.commit()
    session.refresh(pedido)
    session.add(DetallePedido(
        pedido_id=pedido.id,
        producto_id=producto_final.id,
        nombre_snapshot="Producto Final Test",
        cantidad=1,
        precio_snapshot=1000.0,
        subtotal_snap=1000.0,
    ))
    session.add(HistorialEstadoPedido(
        pedido_id=pedido.id,
        estado_desde=None,
        estado_hacia="PENDIENTE",
        usuario_id=client_user.id,
        motivo="Pedido creado",
    ))
    session.commit()
    pid = pedido.id
    session.expunge(pedido)
    pedido.id = pid
    return pedido

class TestCrearPago:

    def test_crear_pago_sin_mp_configurado(
        self, monkeypatch, client: TestClient, session: Session, client_user, pedido_mp_pendiente
    ):
        monkeypatch.setattr("app.modules.pago.service.settings.MP_ACCESS_TOKEN", "")
        set_auth_cookie(client, session, client_user)
        res = client.post(f"{BASE}/create-preference", json={"pedido_id": pedido_mp_pendiente.id})
        clear_auth_cookie(client)
        assert res.status_code in (400, 422, 500)
        assert "MercadoPago" in res.json()["detail"]

    def test_crear_pago_pedido_ajeno(self, client: TestClient, session: Session, admin_user, pedido_mp_pendiente):
        set_auth_cookie(client, session, admin_user)
        res = client.post(f"{BASE}/create-preference", json={"pedido_id": pedido_mp_pendiente.id})
        clear_auth_cookie(client)
        assert res.status_code in (401, 403)

    def test_crear_pago_forma_pago_incorrecta(self, client: TestClient, session: Session, client_user, pedido_efectivo_pendiente):
        set_auth_cookie(client, session, client_user)
        res = client.post(f"{BASE}/create-preference", json={"pedido_id": pedido_efectivo_pendiente.id})
        clear_auth_cookie(client)
        assert res.status_code in (400, 422)

    def test_crear_pago_pedido_inexistente(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.post(f"{BASE}/create-preference", json={"pedido_id": 999999})
        clear_auth_cookie(client)
        assert res.status_code == 404

    def test_crear_pago_sin_autenticar(self, client: TestClient, pedido_mp_pendiente):
        res = client.post(f"{BASE}/create-preference", json={"pedido_id": pedido_mp_pendiente.id})
        assert res.status_code in (401, 403)  # require_role sin auth devuelve 403

    def test_crear_pago_pedido_no_pendiente(self, client: TestClient, session: Session, client_user, pedidos_user, pedido_mp_pendiente):
        set_auth_cookie(client, session, pedidos_user)
        client.patch(
            f"{BASE_PED}/{pedido_mp_pendiente.id}/avanzar",
            json={"nuevo_estado": "CONFIRMADO"},
        )
        clear_auth_cookie(client)

        set_auth_cookie(client, session, client_user)
        res = client.post(f"{BASE}/create-preference", json={"pedido_id": pedido_mp_pendiente.id})
        clear_auth_cookie(client)
        assert res.status_code in (400, 409, 422)


class TestWebhook:

    def test_webhook_sin_datos(self, client: TestClient):
        res = client.post(f"{BASE}/webhook", json={})
        assert res.status_code == 200
        assert res.json()["status"] == "ignored"

    def test_webhook_topic_desconocido(self, client: TestClient):
        res = client.post(f"{BASE}/webhook", json={
            "type": "merchant_order",
            "data": {"id": "123"},
        })
        assert res.status_code == 200
        assert res.json()["status"] == "ignored"

    def test_webhook_sin_payment_id(self, client: TestClient):
        res = client.post(f"{BASE}/webhook", json={
            "type": "payment",
            "data": {},
        })
        assert res.status_code == 200
        assert res.json()["status"] == "ignored"

    def test_webhook_es_publico(self, client: TestClient):
        res = client.post(f"{BASE}/webhook", json={})
        assert res.status_code != 401

    def test_webhook_payment_id_invalido(self, client: TestClient):
        res = client.post(f"{BASE}/webhook", json={
            "type": "payment",
            "data": {"id": "999999999"},
        })
        assert res.status_code == 200