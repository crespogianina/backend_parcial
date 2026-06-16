import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import set_auth_cookie, clear_auth_cookie

BASE = "/api/v1/pedidos"


class TestCrearPedido:

    def test_crear_pedido_efectivo(self, client: TestClient, session: Session, client_user, producto_final, seed_formas_pago, seed_estados_pedido):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json={
            "items": [{"producto_id": producto_final.id, "cantidad": 1}],
            "forma_pago_codigo": "EFECTIVO",
        })
        clear_auth_cookie(client)
        assert res.status_code == 201
        body = res.json()
        assert body["estado_codigo"] == "PENDIENTE"
        assert float(body["total"]) > 0

    def test_crear_pedido_sin_autenticar(self, client: TestClient, producto_final, seed_formas_pago):
        res = client.post(BASE, json={
            "items": [{"producto_id": producto_final.id, "cantidad": 1}],
            "forma_pago_codigo": "EFECTIVO",
        })
        assert res.status_code in (401, 403)

    def test_crear_pedido_admin_no_puede(self, client: TestClient, session: Session, admin_user, producto_final, seed_formas_pago):
        set_auth_cookie(client, session, admin_user)
        res = client.post(BASE, json={
            "items": [{"producto_id": producto_final.id, "cantidad": 1}],
            "forma_pago_codigo": "EFECTIVO",
        })
        clear_auth_cookie(client)
        assert res.status_code == 403

    def test_crear_pedido_forma_pago_invalida(self, client: TestClient, session: Session, client_user, producto_final, seed_formas_pago, seed_estados_pedido):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json={
            "items": [{"producto_id": producto_final.id, "cantidad": 1}],
            "forma_pago_codigo": "NO_EXISTE",
        })
        clear_auth_cookie(client)
        assert res.status_code == 404

    def test_crear_pedido_stock_insuficiente(self, client: TestClient, session: Session, client_user, producto_final, seed_formas_pago, seed_estados_pedido):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json={
            "items": [{"producto_id": producto_final.id, "cantidad": 9999}],
            "forma_pago_codigo": "EFECTIVO",
        })
        clear_auth_cookie(client)
        assert res.status_code == 400

    def test_crear_pedido_mercadopago_sin_direccion(self, client: TestClient, session: Session, client_user, producto_final, seed_formas_pago, seed_estados_pedido):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json={
            "items": [{"producto_id": producto_final.id, "cantidad": 1}],
            "forma_pago_codigo": "MERCADOPAGO",
        })
        clear_auth_cookie(client)
        assert res.status_code == 422

    def test_crear_pedido_sin_items(self, client: TestClient, session: Session, client_user, seed_formas_pago, seed_estados_pedido):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json={
            "items": [],
            "forma_pago_codigo": "EFECTIVO",
        })
        clear_auth_cookie(client)
        assert res.status_code == 422


class TestListarPedidos:

    def test_cliente_ve_solo_sus_pedidos(self, client: TestClient, session: Session, client_user, pedido_pendiente):
        set_auth_cookie(client, session, client_user)
        res = client.get(BASE)
        clear_auth_cookie(client)
        assert res.status_code == 200
        body = res.json()
        assert body["total"] >= 1

    def test_admin_ve_todos_los_pedidos(self, client: TestClient, session: Session, admin_user, pedido_pendiente):
        set_auth_cookie(client, session, admin_user)
        res = client.get(BASE)
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["total"] >= 1

    def test_listar_sin_autenticar(self, client: TestClient):
        res = client.get(BASE)
        assert res.status_code in (401, 403)


class TestObtenerPedido:

    def test_cliente_obtiene_pedido_propio(self, client: TestClient, session: Session, client_user, pedido_pendiente):
        set_auth_cookie(client, session, client_user)
        res = client.get(f"{BASE}/{pedido_pendiente.id}")
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["id"] == pedido_pendiente.id

    def test_admin_obtiene_cualquier_pedido(self, client: TestClient, session: Session, admin_user, pedido_pendiente):
        set_auth_cookie(client, session, admin_user)
        res = client.get(f"{BASE}/{pedido_pendiente.id}")
        clear_auth_cookie(client)
        assert res.status_code == 200

    def test_pedido_inexistente(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.get(f"{BASE}/999999")
        clear_auth_cookie(client)
        assert res.status_code == 404


class TestFSMPedido:

    def test_avanzar_pendiente_a_confirmado(self, client: TestClient, session: Session, pedidos_user, pedido_pendiente):
        set_auth_cookie(client, session, pedidos_user)
        res = client.patch(
            f"{BASE}/{pedido_pendiente.id}/avanzar",
            json={"nuevo_estado": "CONFIRMADO"},
        )
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["estado_codigo"] == "CONFIRMADO"

    def test_transicion_invalida(self, client: TestClient, session: Session, pedidos_user, pedido_pendiente):
        set_auth_cookie(client, session, pedidos_user)
        res = client.patch(
            f"{BASE}/{pedido_pendiente.id}/avanzar",
            json={"nuevo_estado": "ENTREGADO"},
        )
        clear_auth_cookie(client)
        assert res.status_code in (400, 422)

    def test_estado_terminal_no_avanza(self, client: TestClient, session: Session, pedidos_user, pedido_pendiente):
        set_auth_cookie(client, session, pedidos_user)
        client.patch(f"{BASE}/{pedido_pendiente.id}/avanzar", json={"nuevo_estado": "CONFIRMADO"})
        client.patch(f"{BASE}/{pedido_pendiente.id}/avanzar", json={"nuevo_estado": "EN_PREPARACION"})
        client.patch(f"{BASE}/{pedido_pendiente.id}/avanzar", json={"nuevo_estado": "ENTREGADO"})
        res = client.patch(
            f"{BASE}/{pedido_pendiente.id}/avanzar",
            json={"nuevo_estado": "CANCELADO"},
        )
        clear_auth_cookie(client)
        assert res.status_code in (400, 422)

    def test_cancelar_requiere_motivo(self, client: TestClient, session: Session, pedidos_user, pedido_confirmado):
        set_auth_cookie(client, session, pedidos_user)
        res = client.patch(
            f"{BASE}/{pedido_confirmado.id}/avanzar",
            json={"nuevo_estado": "CANCELADO"},
        )
        clear_auth_cookie(client)
        assert res.status_code == 422

    def test_avanzar_sin_permiso(self, client: TestClient, session: Session, client_user, pedido_pendiente):
        set_auth_cookie(client, session, client_user)
        res = client.patch(
            f"{BASE}/{pedido_pendiente.id}/avanzar",
            json={"nuevo_estado": "CONFIRMADO"},
        )
        clear_auth_cookie(client)
        assert res.status_code == 403


class TestHistorialPedido:

    def test_historial_tiene_registro_inicial(self, client: TestClient, session: Session, client_user, pedido_pendiente):
        set_auth_cookie(client, session, client_user)
        res = client.get(f"{BASE}/{pedido_pendiente.id}/historial")
        clear_auth_cookie(client)
        assert res.status_code == 200
        historial = res.json()
        assert len(historial) >= 1
        assert historial[0]["estado_desde"] is None
        assert historial[0]["estado_hacia"] == "PENDIENTE"

    def test_historial_orden_ascendente(self, client: TestClient, session: Session, client_user, pedidos_user, pedido_pendiente):
        set_auth_cookie(client, session, pedidos_user)
        client.patch(
            f"{BASE}/{pedido_pendiente.id}/avanzar",
            json={"nuevo_estado": "CONFIRMADO"},
        )
        clear_auth_cookie(client)

        set_auth_cookie(client, session, client_user)
        res = client.get(f"{BASE}/{pedido_pendiente.id}/historial")
        clear_auth_cookie(client)
        historial = res.json()
        fechas = [h["created_at"] for h in historial]
        assert fechas == sorted(fechas)


class TestCancelarPedidoPropio:

    def test_cliente_cancela_pedido_propio(self, client: TestClient, session: Session, client_user, pedido_pendiente):
        set_auth_cookie(client, session, client_user)
        res = client.delete(f"{BASE}/{pedido_pendiente.id}")
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["estado_codigo"] == "CANCELADO"

    def test_cliente_no_puede_cancelar_pedido_ajeno(self, client: TestClient, session: Session, admin_user, pedido_pendiente):
        set_auth_cookie(client, session, admin_user)
        res = client.delete(f"{BASE}/{pedido_pendiente.id}")
        clear_auth_cookie(client)
        assert res.status_code == 403