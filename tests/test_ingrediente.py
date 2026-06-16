import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import set_auth_cookie, clear_auth_cookie

BASE = "/api/v1/ingredientes"


class TestCrearIngrediente:

    def test_crear_ingrediente_exitoso(self, client: TestClient, session: Session, admin_user, unidad_g):
        set_auth_cookie(client, session, admin_user)
        res = client.post(BASE, json={
            "nombre": "Queso cheddar",
            "descripcion": "Queso amarillo",
            "es_alergeno": True,
            "stock_cantidad": 500,
            "unidad_medida_id": unidad_g.id,
            "precio_base": 20.0,
        })
        clear_auth_cookie(client)
        assert res.status_code == 201
        body = res.json()
        assert body["nombre"] == "Queso cheddar"
        assert body["es_alergeno"] is True
        assert body["activo"] is True

    def test_crear_ingrediente_nombre_duplicado(self, client: TestClient, session: Session, admin_user, ingrediente_base):
        set_auth_cookie(client, session, admin_user)
        res = client.post(BASE, json={
            "nombre": ingrediente_base.nombre,
            "descripcion": "Duplicado",
            "es_alergeno": False,
            "stock_cantidad": 100,
            "unidad_medida_id": ingrediente_base.unidad_medida_id,
            "precio_base": 10.0,
        })
        clear_auth_cookie(client)
        assert res.status_code == 409

    def test_crear_ingrediente_sin_autenticar(self, client: TestClient, unidad_g):
        res = client.post(BASE, json={
            "nombre": "Sin auth",
            "descripcion": "Test",
            "es_alergeno": False,
            "stock_cantidad": 100,
            "unidad_medida_id": unidad_g.id,
            "precio_base": 10.0,
        })
        assert res.status_code == 401

    def test_crear_ingrediente_sin_permiso(self, client: TestClient, session: Session, client_user, unidad_g):
        set_auth_cookie(client, session, client_user)
        res = client.post(BASE, json={
            "nombre": "Sin permiso",
            "descripcion": "Test",
            "es_alergeno": False,
            "stock_cantidad": 100,
            "unidad_medida_id": unidad_g.id,
            "precio_base": 10.0,
        })
        clear_auth_cookie(client)
        assert res.status_code == 403

    def test_crear_ingrediente_unidad_invalida(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.post(BASE, json={
            "nombre": "Sin unidad",
            "descripcion": "Test",
            "es_alergeno": False,
            "stock_cantidad": 100,
            "unidad_medida_id": 999999,
            "precio_base": 10.0,
        })
        clear_auth_cookie(client)
        assert res.status_code == 404


class TestListarIngredientes:

    def test_listar_ingredientes_admin(self, client: TestClient, session: Session, admin_user, ingrediente_base):
        set_auth_cookie(client, session, admin_user)
        res = client.get(BASE)
        clear_auth_cookie(client)
        assert res.status_code == 200
        body = res.json()
        assert "data" in body
        assert body["total"] >= 1

    def test_listar_ingredientes_stock(self, client: TestClient, session: Session, stock_user, ingrediente_base):
        set_auth_cookie(client, session, stock_user)
        res = client.get(BASE)
        clear_auth_cookie(client)
        assert res.status_code == 200

    def test_listar_ingredientes_sin_permiso(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.get(BASE)
        clear_auth_cookie(client)
        assert res.status_code == 403

    def test_listar_sin_autenticar(self, client: TestClient):
        res = client.get(BASE)
        assert res.status_code == 401


class TestObtenerIngrediente:

    def test_obtener_ingrediente_por_id(self, client: TestClient, session: Session, admin_user, ingrediente_base):
        set_auth_cookie(client, session, admin_user)
        res = client.get(f"{BASE}/{ingrediente_base.id}")
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["id"] == ingrediente_base.id

    def test_ingrediente_inexistente(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.get(f"{BASE}/999999")
        clear_auth_cookie(client)
        assert res.status_code == 404


class TestActualizarIngrediente:

    def test_actualizar_ingrediente(self, client: TestClient, session: Session, admin_user, ingrediente_base, unidad_g):
        set_auth_cookie(client, session, admin_user)
        res = client.put(f"{BASE}/{ingrediente_base.id}", json={
            "nombre": "Carne actualizada",
            "descripcion": "Actualizada",
            "es_alergeno": False,
            "stock_cantidad": 200,
            "unidad_medida_id": unidad_g.id,
            "precio_base": 150.0,
        })
        clear_auth_cookie(client)
        assert res.status_code == 200
        assert res.json()["nombre"] == "Carne actualizada"

    def test_actualizar_ingrediente_sin_permiso(self, client: TestClient, session: Session, client_user, ingrediente_base, unidad_g):
        set_auth_cookie(client, session, client_user)
        res = client.put(f"{BASE}/{ingrediente_base.id}", json={
            "nombre": "No permitido",
            "descripcion": "Test",
            "es_alergeno": False,
            "stock_cantidad": 100,
            "unidad_medida_id": unidad_g.id,
            "precio_base": 10.0,
        })
        clear_auth_cookie(client)
        assert res.status_code == 403


class TestEliminarIngrediente:

    def test_soft_delete_ingrediente(self, client: TestClient, session: Session, admin_user, unidad_g):
        set_auth_cookie(client, session, admin_user)
        res = client.post(BASE, json={
            "nombre": "A eliminar",
            "descripcion": "Test",
            "es_alergeno": False,
            "stock_cantidad": 10,
            "unidad_medida_id": unidad_g.id,
            "precio_base": 5.0,
        })
        assert res.status_code == 201
        ing_id = res.json()["id"]

        res = client.delete(f"{BASE}/{ing_id}")
        assert res.status_code == 200

        res = client.get(f"{BASE}/{ing_id}")
        assert res.status_code == 404

        clear_auth_cookie(client)

    def test_eliminar_sin_permiso(self, client: TestClient, session: Session, client_user, ingrediente_base):
        set_auth_cookie(client, session, client_user)
        res = client.delete(f"{BASE}/{ingrediente_base.id}")
        clear_auth_cookie(client)
        assert res.status_code == 403