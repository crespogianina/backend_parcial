import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import get_auth_headers

BASE_PED = "/api/v1/pedidos"
WS_BASE = "/ws/pedidos"


def _get_token(session: Session, user) -> str:
    headers = get_auth_headers(session, user)
    return headers["access_token"]


class TestConexionWebSocket:

    def test_conexion_cliente_propio(self, client: TestClient, session: Session, client_user, pedido_pendiente):
        token = _get_token(session, client_user)
        with client.websocket_connect(f"{WS_BASE}/{pedido_pendiente.id}?token={token}") as ws:
            assert ws is not None

    def test_conexion_sin_token(self, client: TestClient, pedido_pendiente):
        with pytest.raises(Exception):
            with client.websocket_connect(f"{WS_BASE}/{pedido_pendiente.id}") as ws:
                ws.receive_json()

    def test_conexion_token_invalido(self, client: TestClient, pedido_pendiente):
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"{WS_BASE}/{pedido_pendiente.id}?token=token.invalido.xxx"
            ) as ws:
                ws.receive_json()

    def test_conexion_pedido_inexistente(self, client: TestClient, session: Session, client_user):
        token = _get_token(session, client_user)
        with pytest.raises(Exception):
            with client.websocket_connect(f"{WS_BASE}/999999?token={token}") as ws:
                ws.receive_json()


class TestEventosWebSocket:

    def test_recibe_evento_al_avanzar_estado(self, client: TestClient, session: Session, client_user, pedidos_user, pedido_pendiente):
        token = _get_token(session, client_user)

        with client.websocket_connect(f"{WS_BASE}/{pedido_pendiente.id}?token={token}") as ws:
            pedidos_headers = get_auth_headers(session, pedidos_user)
            res = client.patch(
                f"{BASE_PED}/{pedido_pendiente.id}/avanzar",
                json={"nuevo_estado": "CONFIRMADO"},
                cookies=pedidos_headers,
            )
            assert res.status_code == 200

            evento = ws.receive_json()
            assert evento["pedido_id"] == pedido_pendiente.id
            assert evento["estado_nuevo"] == "CONFIRMADO"

    def test_evento_contiene_campos_requeridos(self, client: TestClient, session: Session, client_user, pedidos_user, pedido_pendiente):
        token = _get_token(session, client_user)

        with client.websocket_connect(f"{WS_BASE}/{pedido_pendiente.id}?token={token}") as ws:
            pedidos_headers = get_auth_headers(session, pedidos_user)
            client.patch(
                f"{BASE_PED}/{pedido_pendiente.id}/avanzar",
                json={"nuevo_estado": "CONFIRMADO"},
                cookies=pedidos_headers,
            )
            evento = ws.receive_json()

            assert "event" in evento
            assert "pedido_id" in evento
            assert "estado_nuevo" in evento
            assert "estado_anterior" in evento
            assert "timestamp" in evento
            assert "usuario_id" in evento

            assert evento["event"] in ("estado_cambiado", "pedido_cancelado", "pago_confirmado")
            assert evento["estado_anterior"] == "PENDIENTE"
            assert evento["estado_nuevo"] == "CONFIRMADO"

    def test_evento_cancelacion(self, client: TestClient, session: Session, client_user, pedido_pendiente):
        token = _get_token(session, client_user)

        with client.websocket_connect(f"{WS_BASE}/{pedido_pendiente.id}?token={token}") as ws:
            client_headers = get_auth_headers(session, client_user)
            res = client.delete(f"{BASE_PED}/{pedido_pendiente.id}", cookies=client_headers)
            assert res.status_code == 200

            evento = ws.receive_json()
            assert evento["event"] == "pedido_cancelado"
            assert evento["estado_nuevo"] == "CANCELADO"
            assert evento["pedido_id"] == pedido_pendiente.id


class TestRBACWebSocket:

    def test_pedido_ajeno_rechazado(self, client: TestClient, session: Session, admin_user, pedido_pendiente):
        token = _get_token(session, admin_user)
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"{WS_BASE}/{pedido_pendiente.id}?token={token}"
            ) as ws:
                ws.receive_json()