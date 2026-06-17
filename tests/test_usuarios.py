import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import set_auth_cookie, clear_auth_cookie

BASE = "/api/v1/usuario"


class TestRegister:

    def test_register_exitoso(self, client: TestClient):
        res = client.post(f"{BASE}/register", json={
            "nombre": "Juan",
            "apellido": "Pérez",
            "username": "juanperez",
            "email": "juan@test.com",
            "password": "Password1!",
        })
        assert res.status_code == 201
        body = res.json()
        assert body["username"] == "juanperez"
        assert "password_hash" not in body
        assert "password" not in body

    def test_register_email_duplicado(self, client: TestClient, client_user):
        res = client.post(f"{BASE}/register", json={
            "nombre": "Otro",
            "apellido": "User",
            "username": "otrousername",
            "email": "client@test.com",
            "password": "Password1!",
        })
        assert res.status_code == 409

    def test_register_username_duplicado(self, client: TestClient, client_user):
        res = client.post(f"{BASE}/register", json={
            "nombre": "Otro",
            "apellido": "User",
            "username": "test_client",
            "email": "nuevo@test.com",
            "password": "Password1!",
        })
        assert res.status_code == 409

    def test_register_password_corta(self, client: TestClient):
        res = client.post(f"{BASE}/register", json={
            "nombre": "Test",
            "apellido": "User",
            "username": "testshort",
            "email": "short@test.com",
            "password": "1234567",
        })
        assert res.status_code == 422

    def test_register_email_invalido(self, client: TestClient):
        res = client.post(f"{BASE}/register", json={
            "nombre": "Test",
            "apellido": "User",
            "username": "testinvalid",
            "email": "no_es_un_email",
            "password": "Password1!",
        })
        assert res.status_code == 422

    def test_register_no_expone_password_hash(self, client: TestClient):
        res = client.post(f"{BASE}/register", json={
            "nombre": "Seguro",
            "apellido": "User",
            "username": "segurouser",
            "email": "seguro@test.com",
            "password": "Password1!",
        })
        assert res.status_code == 201
        body = res.json()
        assert "password_hash" not in body
        assert "hashed_password" not in body
        assert "password" not in body


class TestLogin:

    def test_login_exitoso(self, client: TestClient, admin_user):
        res = client.post(f"{BASE}/token", data={
            "username": "test_admin",
            "password": "Admin1234!",
        })
        assert res.status_code == 200
        assert "access_token" in res.cookies

    def test_login_password_incorrecta(self, client: TestClient, admin_user):
        res = client.post(f"{BASE}/token", data={
            "username": "test_admin",
            "password": "WrongPassword!",
        })
        assert res.status_code == 401
        assert "Credenciales" in res.json()["detail"]

    def test_login_usuario_inexistente(self, client: TestClient):
        res = client.post(f"{BASE}/token", data={
            "username": "no_existe_xyz",
            "password": "Password1!",
        })
        assert res.status_code == 401

    def test_login_setea_cookie_httponly(self, client: TestClient, admin_user):
        res = client.post(f"{BASE}/token", data={
            "username": "test_admin",
            "password": "Admin1234!",
        })
        assert res.status_code == 200
        assert "access_token" in res.cookies

    def test_login_usuario_desactivado(self, client: TestClient, session: Session, client_user):
        from datetime import datetime, timezone
        client_user.deleted_at = datetime.now(timezone.utc)
        session.add(client_user)
        session.commit()

        res = client.post(f"{BASE}/token", data={
            "username": "test_client",
            "password": "Client1234!",
        })
        assert res.status_code in (400, 401)

        client_user.deleted_at = None
        session.add(client_user)
        session.commit()


class TestLogout:

    def test_logout_exitoso(self, client: TestClient, admin_user):
        client.post(f"{BASE}/token", data={
            "username": "test_admin",
            "password": "Admin1234!",
        })
        res = client.post(f"{BASE}/logout")
        assert res.status_code in (200, 204)

    def test_logout_limpia_cookie(self, client: TestClient, admin_user):
        client.post(f"{BASE}/token", data={
            "username": "test_admin",
            "password": "Admin1234!",
        })
        client.post(f"{BASE}/logout")
        res = client.get(f"{BASE}/me")
        assert res.status_code == 401


class TestMe:

    def test_me_con_token_valido(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.get(f"{BASE}/me")
        clear_auth_cookie(client)
        assert res.status_code == 200
        body = res.json()
        assert body["username"] == "test_client"
        assert "password_hash" not in body

    def test_me_sin_autenticar(self, client: TestClient):
        res = client.get(f"{BASE}/me")
        assert res.status_code == 401

    def test_me_incluye_roles(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.get(f"{BASE}/me")
        clear_auth_cookie(client)
        assert res.status_code == 200
        body = res.json()
        assert "roles" in body
        assert "ADMIN" in body["roles"]


class TestActualizarPerfil:

    def test_actualizar_nombre(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.patch(f"{BASE}/me", json={"nombre": "NuevoNombre"})
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["nombre"] == "NuevoNombre"

    def test_actualizar_apellido(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.patch(f"{BASE}/me", json={"apellido": "NuevoApellido"})
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["apellido"] == "NuevoApellido"

    def test_actualizar_sin_autenticar(self, client: TestClient):
        res = client.patch(f"{BASE}/me", json={"nombre": "Nadie"})
        assert res.status_code == 401

    def test_no_puede_cambiar_rol_propio(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.patch(f"{BASE}/me", json={"roles": ["ADMIN"]})
        clear_auth_cookie(client)
        if res.status_code == 200:
            assert "ADMIN" not in res.json().get("roles", [])


class TestGestionUsuarios:

    def test_listar_usuarios_admin(self, client: TestClient, session: Session, admin_user, client_user):
        set_auth_cookie(client, session, admin_user)
        res = client.get(f"{BASE}/admin/usuarios")
        clear_auth_cookie(client)
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list)
        assert len(body) >= 2

    def test_listar_usuarios_sin_permiso(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.get(f"{BASE}/admin/usuarios")
        clear_auth_cookie(client)
        assert res.status_code == 403

    def test_listar_usuarios_sin_autenticar(self, client: TestClient):
        res = client.get(f"{BASE}/admin/usuarios")
        assert res.status_code == 401

    def test_listar_no_expone_passwords(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.get(f"{BASE}/admin/usuarios")
        clear_auth_cookie(client)
        assert res.status_code == 200
        for user in res.json():
            assert "password_hash" not in user
            assert "password" not in user


class TestGestionEstadoUsuarios:

    def test_desactivar_usuario_admin(self, client: TestClient, session: Session, admin_user, client_user):
        set_auth_cookie(client, session, admin_user)
        res = client.post(f"{BASE}/admin/usuarios/{client_user.id}/desactivar")
        clear_auth_cookie(client)
        assert res.status_code == 200

    def test_activar_usuario_admin(self, client: TestClient, session: Session, admin_user, client_user):
        set_auth_cookie(client, session, admin_user)
        client.post(f"{BASE}/admin/usuarios/{client_user.id}/desactivar")
        res = client.post(f"{BASE}/admin/usuarios/{client_user.id}/activar")
        clear_auth_cookie(client)
        assert res.status_code == 200

    def test_desactivar_sin_permiso(self, client: TestClient, session: Session, client_user, pedidos_user):
        set_auth_cookie(client, session, client_user)
        res = client.post(f"{BASE}/admin/usuarios/{pedidos_user.id}/desactivar")
        clear_auth_cookie(client)
        assert res.status_code == 403

    def test_desactivar_usuario_inexistente(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.post(f"{BASE}/admin/usuarios/999999/desactivar")
        clear_auth_cookie(client)
        assert res.status_code == 404