import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import get_auth_headers

BASE = "/api/v1/categorias"


class TestCrearCategoria:
    def test_crear_categoria_exitoso(self, client: TestClient, session: Session, admin_user):
        headers = get_auth_headers(session, admin_user)
        res = client.post(BASE, json={"nombre": "Hamburguesas"}, cookies=headers)
        assert res.status_code == 201
        assert res.json()["nombre"] == "Hamburguesas"
        assert res.json()["activo"] is True

    def test_crear_categoria_sin_autenticar(self, client: TestClient):
        res = client.post(BASE, json={"nombre": "Sin auth"})
        assert res.status_code == 401

    def test_crear_categoria_sin_permiso(self, client: TestClient, session: Session, client_user):
        headers = get_auth_headers(session, client_user)
        res = client.post(BASE, json={"nombre": "Sin permiso"}, cookies=headers)
        assert res.status_code == 403

    def test_crear_categoria_nombre_duplicado(self, client: TestClient, session: Session, admin_user):
        headers = get_auth_headers(session, admin_user)
        client.post(BASE, json={"nombre": "Duplicada"}, cookies=headers)
        res = client.post(BASE, json={"nombre": "Duplicada"}, cookies=headers)
        assert res.status_code == 409

    def test_crear_categoria_con_descripcion(self, client: TestClient, session: Session, admin_user):
        headers = get_auth_headers(session, admin_user)
        res = client.post(BASE, json={"nombre": "Postres", "descripcion": "Dulces y postres"}, cookies=headers)
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
        headers = get_auth_headers(session, admin_user)
        for i in range(3):
            client.post(BASE, json={"nombre": f"Cat Pag {i}"}, cookies=headers)
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
        headers = get_auth_headers(session, admin_user)
        res = client.put(f"{BASE}/{categoria_base.id}", json={"nombre": "Nombre actualizado"}, cookies=headers)
        assert res.status_code == 200
        assert res.json()["nombre"] == "Nombre actualizado"

    def test_actualizar_categoria_sin_permiso(self, client: TestClient, session: Session, client_user, categoria_base):
        headers = get_auth_headers(session, client_user)
        res = client.put(f"{BASE}/{categoria_base.id}", json={"nombre": "No permitido"}, cookies=headers)
        assert res.status_code == 403

    def test_actualizar_categoria_inexistente(self, client: TestClient, session: Session, admin_user):
        headers = get_auth_headers(session, admin_user)
        res = client.put(f"{BASE}/999999", json={"nombre": "No existe"}, cookies=headers)
        assert res.status_code == 404


class TestEliminarCategoria:
    def test_soft_delete_categoria(self, client: TestClient, session: Session, admin_user):
        headers = get_auth_headers(session, admin_user)
        res = client.post(BASE, json={"nombre": "A eliminar"}, cookies=headers)
        cat_id = res.json()["id"]

        res = client.delete(f"{BASE}/{cat_id}", cookies=headers)
        assert res.status_code == 200

        res = client.get(f"{BASE}/{cat_id}")
        assert res.status_code == 404

    def test_eliminar_sin_permiso(self, client: TestClient, session: Session, client_user, categoria_base):
        headers = get_auth_headers(session, client_user)
        res = client.delete(f"{BASE}/{categoria_base.id}", cookies=headers)
        assert res.status_code == 403