import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import set_auth_cookie, clear_auth_cookie

BASE = "/api/v1/categorias"


class TestCrearCategoria:

    def test_crear_categoria_exitoso(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.post(BASE, json={"nombre": "Hamburguesas"})
        clear_auth_cookie(client)
        assert res.status_code == 201
        assert res.json()["nombre"] == "Hamburguesas"
        assert res.json()["activo"] is True

    def test_crear_categoria_sin_autenticar(self, client: TestClient):
        res = client.post(BASE, json={"nombre": "Sin auth"})
        assert res.status_code == 401

    def test_crear_categoria_sin_permiso(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json={"nombre": "Sin permiso"})
        clear_auth_cookie(client)
        assert res.status_code == 403

    def test_crear_categoria_nombre_duplicado(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        client.post(BASE, json={"nombre": "Duplicada"})
        res = client.post(BASE, json={"nombre": "Duplicada"})
        clear_auth_cookie(client)
        assert res.status_code == 409

    def test_crear_categoria_con_descripcion(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.post(BASE, json={"nombre": "Postres", "descripcion": "Dulces y postres"})
        clear_auth_cookie(client)
        assert res.status_code == 201
        assert res.json()["descripcion"] == "Dulces y postres"


class TestListarCategorias:

    def test_listar_categorias_publico(self, client: TestClient, categoria_base):
        res = client.get(BASE)
        assert res.status_code == 200
        body = res.json()
        assert "data" in body
        assert "total" in body
        assert body["total"] >= 1

    def test_listar_categorias_paginacion(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        for i in range(3):
            client.post(BASE, json={"nombre": f"Cat Pag {i}"})
        clear_auth_cookie(client)
        res = client.get(f"{BASE}?limit=2&offset=0")
        assert res.status_code == 200
        assert len(res.json()["data"]) <= 2


class TestObtenerCategoria:

    def test_obtener_categoria_por_id(self, client: TestClient, categoria_base):
        res = client.get(f"{BASE}/{categoria_base.id}")
        assert res.status_code == 200
        assert res.json()["id"] == categoria_base.id

    def test_categoria_inexistente(self, client: TestClient):
        res = client.get(f"{BASE}/999999")
        assert res.status_code == 404


class TestActualizarCategoria:

    def test_actualizar_categoria(self, client: TestClient, session: Session, admin_user, categoria_base):
        set_auth_cookie(client, session, admin_user)
        res = client.put(f"{BASE}/{categoria_base.id}", json={"nombre": "Nombre actualizado"})
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["nombre"] == "Nombre actualizado"

    def test_actualizar_categoria_sin_permiso(self, client: TestClient, session: Session, client_user, categoria_base):
        set_auth_cookie(client, session, client_user)
        res = client.put(f"{BASE}/{categoria_base.id}", json={"nombre": "No permitido"})
        clear_auth_cookie(client)
        assert res.status_code == 403

    def test_actualizar_categoria_inexistente(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.put(f"{BASE}/999999", json={"nombre": "No existe"})
        clear_auth_cookie(client)
        assert res.status_code == 404


class TestEliminarCategoria:

    def test_soft_delete_categoria(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.post(BASE, json={"nombre": "A eliminar"})
        assert res.status_code == 201
        cat_id = res.json()["id"]

        res = client.delete(f"{BASE}/{cat_id}")
        assert res.status_code == 200

        clear_auth_cookie(client)
        res = client.get(f"{BASE}/{cat_id}")
        assert res.status_code == 404

    def test_eliminar_sin_permiso(self, client: TestClient, session: Session, client_user, categoria_base):
        set_auth_cookie(client, session, client_user)
        res = client.delete(f"{BASE}/{categoria_base.id}")
        clear_auth_cookie(client)
        assert res.status_code == 403