
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
 
from tests.conftest import set_auth_cookie, clear_auth_cookie
 
BASE = "/api/v1/direcciones"
 
 
def _payload(alias="Casa", linea1="Av. Siempre Viva 742", ciudad="Buenos Aires"):
    return {
        "alias": alias,
        "linea1": linea1,
        "ciudad": ciudad,
        "provincia": "Buenos Aires",
        "codigo_postal": "1234",
        "es_principal": False,
    }
 
 
@pytest.fixture(name="direccion_base")
def direccion_base_fixture(client: TestClient, session: Session, client_user):
    set_auth_cookie(client, session, client_user)
    res = client.post(BASE, json=_payload())
    clear_auth_cookie(client)
    assert res.status_code == 201
    return res.json()
 
 
@pytest.fixture(name="client_user_2")
def client_user_2_fixture(session: Session):
    from app.modules.usuarios.model import Usuario, UsuarioRol
    from app.core.security import hash_password
    user = Usuario(
        username="test_client_2",
        nombre="Test",
        apellido="Client2",
        email="client2@test.com",
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
 
 
class TestCrearDireccion:
 
    def test_crear_direccion_exitoso(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json=_payload("Trabajo", "Calle Falsa 123", "Mendoza"))
        clear_auth_cookie(client)
        assert res.status_code == 201
        body = res.json()
        assert body["alias"] == "Trabajo"
        assert body["ciudad"] == "Mendoza"
        assert body["es_principal"] is False
 
    def test_crear_direccion_sin_autenticar(self, client: TestClient):
        res = client.post(BASE, json=_payload())
        assert res.status_code == 401
 
    def test_crear_direccion_admin_no_puede(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.post(BASE, json=_payload())
        clear_auth_cookie(client)
        assert res.status_code == 403
 
    def test_crear_direccion_como_principal(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json={**_payload(), "es_principal": True})
        clear_auth_cookie(client)
        assert res.status_code == 201
        assert res.json()["es_principal"] is True
 
    def test_crear_direccion_sin_ciudad_invalido(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json={**_payload(), "ciudad": ""})
        clear_auth_cookie(client)
        assert res.status_code == 422
 
    def test_crear_direccion_sin_linea1_invalido(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json={**_payload(), "linea1": ""})
        clear_auth_cookie(client)
        assert res.status_code == 422
 
 
class TestListarDirecciones:
 
    def test_listar_propias(self, client: TestClient, session: Session, client_user, direccion_base):
        set_auth_cookie(client, session, client_user)
        res = client.get(BASE)
        clear_auth_cookie(client)
        assert res.status_code == 200
        body = res.json()
        assert "data" in body
        assert body["total"] >= 1
        ids = [d["id"] for d in body["data"]]
        assert direccion_base["id"] in ids
 
    def test_no_ve_direcciones_ajenas(self, client: TestClient, session: Session, client_user, client_user_2, direccion_base):
        set_auth_cookie(client, session, client_user_2)
        client.post(BASE, json=_payload("Oficina", "Otra calle 456", "Córdoba"))
        clear_auth_cookie(client)
 
        set_auth_cookie(client, session, client_user)
        res = client.get(BASE)
        clear_auth_cookie(client)
        for d in res.json()["data"]:
            assert d["id"] == direccion_base["id"]
 
    def test_listar_sin_autenticar(self, client: TestClient):
        res = client.get(BASE)
        assert res.status_code == 401
 
 
class TestObtenerDireccion:
 
    def test_obtener_propia(self, client: TestClient, session: Session, client_user, direccion_base):
        set_auth_cookie(client, session, client_user)
        res = client.get(f"{BASE}/{direccion_base['id']}")
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["id"] == direccion_base["id"]
 
    def test_no_puede_ver_ajena(self, client: TestClient, session: Session, client_user_2, direccion_base):
        set_auth_cookie(client, session, client_user_2)
        res = client.get(f"{BASE}/{direccion_base['id']}")
        clear_auth_cookie(client)
        assert res.status_code in (403, 404)
 
    def test_direccion_inexistente(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.get(f"{BASE}/999999")
        clear_auth_cookie(client)
        assert res.status_code == 404
 
 
class TestActualizarDireccion:
 
    def test_actualizar_propia(self, client: TestClient, session: Session, client_user, direccion_base):
        set_auth_cookie(client, session, client_user)
        res = client.put(
            f"{BASE}/{direccion_base['id']}",
            json={**_payload(), "alias": "Casa actualizada", "linea1": "Nueva calle 999"},
        )
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["alias"] == "Casa actualizada"
        assert res.json()["linea1"] == "Nueva calle 999"
 
    def test_no_puede_actualizar_ajena(self, client: TestClient, session: Session, client_user_2, direccion_base):
        set_auth_cookie(client, session, client_user_2)
        res = client.put(f"{BASE}/{direccion_base['id']}", json=_payload("Hackeado"))
        clear_auth_cookie(client)
        assert res.status_code in (403, 404)
 
    def test_actualizar_sin_autenticar(self, client: TestClient, direccion_base):
        res = client.put(f"{BASE}/{direccion_base['id']}", json=_payload())
        assert res.status_code == 401
 
 
class TestMarcarPrincipal:
 
    def test_marcar_principal(self, client: TestClient, session: Session, client_user, direccion_base):
        set_auth_cookie(client, session, client_user)
        res = client.patch(f"{BASE}/{direccion_base['id']}/principal")
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["es_principal"] is True
 
    def test_solo_una_principal_por_usuario(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
 
        res1 = client.post(BASE, json=_payload("Dir1", "Calle 1", "BA"))
        res2 = client.post(BASE, json=_payload("Dir2", "Calle 2", "BA"))
        assert res1.status_code == 201
        assert res2.status_code == 201
        id1 = res1.json()["id"]
        id2 = res2.json()["id"]
 
        client.patch(f"{BASE}/{id1}/principal")
        client.patch(f"{BASE}/{id2}/principal")
 
        res = client.get(f"{BASE}/{id1}")
        assert res.json()["es_principal"] is False
 
        res = client.get(f"{BASE}/{id2}")
        assert res.json()["es_principal"] is True
 
        clear_auth_cookie(client)
 
    def test_no_puede_marcar_principal_ajena(self, client: TestClient, session: Session, client_user_2, direccion_base):
        """El service filtra por usuario_id — devuelve 404 (no revela que existe)"""
        set_auth_cookie(client, session, client_user_2)
        res = client.patch(f"{BASE}/{direccion_base['id']}/principal")
        clear_auth_cookie(client)
        assert res.status_code in (403, 404)
 
 
class TestEliminarDireccion:
 
    def test_eliminar_propia(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json=_payload("A eliminar", "Calle X", "BA"))
        assert res.status_code == 201
        dir_id = res.json()["id"]
 
        res = client.delete(f"{BASE}/{dir_id}")
        assert res.status_code == 200
 
        res = client.get(f"{BASE}/{dir_id}")
        assert res.status_code == 404
 
        clear_auth_cookie(client)
 
    def test_no_puede_eliminar_ajena(self, client: TestClient, session: Session, client_user_2, direccion_base):
        """El service filtra por usuario_id — devuelve 404 (no revela que existe)"""
        set_auth_cookie(client, session, client_user_2)
        res = client.delete(f"{BASE}/{direccion_base['id']}")
        clear_auth_cookie(client)
        assert res.status_code in (403, 404)
 
    def test_eliminar_sin_autenticar(self, client: TestClient, direccion_base):
        res = client.delete(f"{BASE}/{direccion_base['id']}")
        assert res.status_code == 401
 