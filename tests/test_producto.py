import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import get_auth_headers

BASE = "/api/v1/productos"


class TestCrearProducto:
    def test_crear_producto_final(self, client: TestClient, session: Session, admin_user, categoria_base, unidad_ud):
        headers = get_auth_headers(session, admin_user)
        res = client.post(BASE, json={
            "nombre": "Coca Cola 500ml",
            "descripcion": "Bebida gaseosa",
            "precio_base": 800.0,
            "es_producto_final": True,
            "stock_cantidad": 20,
            "unidad_medida_id": unidad_ud.id,
            "categorias": [{"categoria_id": categoria_base.id, "es_principal": True}],
            "ingredientes": [],
        }, cookies=headers)
        assert res.status_code == 201
        body = res.json()
        assert body["es_producto_final"] is True
        assert body["stock_cantidad"] == 20

    def test_crear_producto_con_ingredientes(self, client: TestClient, session: Session, admin_user, categoria_base, ingrediente_base, unidad_g):
        headers = get_auth_headers(session, admin_user)
        res = client.post(BASE, json={
            "nombre": "Hamburguesa Clásica",
            "descripcion": "Con carne y queso",
            "precio_base": 2500.0,
            "es_producto_final": False,
            "categorias": [{"categoria_id": categoria_base.id, "es_principal": True}],
            "ingredientes": [{
                "ingrediente_id": ingrediente_base.id,
                "es_removible": False,
                "unidad_medida_id": unidad_g.id,
                "cantidad": 150,
            }],
        }, cookies=headers)
        assert res.status_code == 201
        assert len(res.json()["ingredientes"]) == 1

    def test_producto_final_no_puede_tener_ingredientes(self, client: TestClient, session: Session, admin_user, categoria_base, ingrediente_base, unidad_g):
        headers = get_auth_headers(session, admin_user)
        res = client.post(BASE, json={
            "nombre": "Inválido",
            "descripcion": "No debería crearse",
            "precio_base": 100.0,
            "es_producto_final": True,
            "stock_cantidad": 5,
            "categorias": [{"categoria_id": categoria_base.id, "es_principal": True}],
            "ingredientes": [{
                "ingrediente_id": ingrediente_base.id,
                "es_removible": False,
                "unidad_medida_id": unidad_g.id,
                "cantidad": 100,
            }],
        }, cookies=headers)
        assert res.status_code == 422

    def test_producto_no_final_requiere_ingredientes(self, client: TestClient, session: Session, admin_user, categoria_base):
        headers = get_auth_headers(session, admin_user)
        res = client.post(BASE, json={
            "nombre": "Sin ingredientes",
            "descripcion": "Inválido",
            "precio_base": 100.0,
            "es_producto_final": False,
            "categorias": [{"categoria_id": categoria_base.id, "es_principal": True}],
            "ingredientes": [],
        }, cookies=headers)
        assert res.status_code == 422

    def test_crear_producto_nombre_duplicado(self, client: TestClient, session: Session, admin_user, categoria_base, unidad_ud):
        headers = get_auth_headers(session, admin_user)
        payload = {
            "nombre": "Producto Duplicado",
            "descripcion": "Test",
            "precio_base": 100.0,
            "es_producto_final": True,
            "stock_cantidad": 5,
            "categorias": [{"categoria_id": categoria_base.id, "es_principal": True}],
            "ingredientes": [],
        }
        client.post(BASE, json=payload, cookies=headers)
        res = client.post(BASE, json=payload, cookies=headers)
        assert res.status_code == 409

    def test_crear_producto_sin_autenticar(self, client: TestClient, categoria_base):
        res = client.post(BASE, json={
            "nombre": "Sin auth",
            "descripcion": "Test",
            "precio_base": 100.0,
            "es_producto_final": True,
            "stock_cantidad": 1,
            "categorias": [{"categoria_id": categoria_base.id, "es_principal": True}],
            "ingredientes": [],
        })
        assert res.status_code == 401

    def test_crear_producto_sin_permiso(self, client: TestClient, session: Session, client_user, categoria_base):
        headers = get_auth_headers(session, client_user)
        res = client.post(BASE, json={
            "nombre": "Sin permiso",
            "descripcion": "Test",
            "precio_base": 100.0,
            "es_producto_final": True,
            "stock_cantidad": 1,
            "categorias": [{"categoria_id": categoria_base.id, "es_principal": True}],
            "ingredientes": [],
        }, cookies=headers)
        assert res.status_code == 403


class TestListarProductos:
    def test_listar_productos_publico(self, client: TestClient, producto_final):
        res = client.get(BASE)
        assert res.status_code == 200
        body = res.json()
        assert "data" in body
        assert body["total"] >= 1

    def test_filtrar_por_disponible(self, client: TestClient, producto_final):
        res = client.get(f"{BASE}?disponible=true")
        assert res.status_code == 200
        for p in res.json()["data"]:
            assert p["disponible"] is True


class TestObtenerProducto:
    def test_obtener_producto_por_id(self, client: TestClient, producto_final):
        res = client.get(f"{BASE}/{producto_final.id}")
        assert res.status_code == 200
        assert res.json()["id"] == producto_final.id

    def test_producto_inexistente(self, client: TestClient):
        res = client.get(f"{BASE}/999999")
        assert res.status_code == 404


class TestStockProducto:
    def test_actualizar_stock_admin(self, client: TestClient, session: Session, admin_user, producto_final):
        headers = get_auth_headers(session, admin_user)
        res = client.patch(f"{BASE}/{producto_final.id}/stock", json={"stock_cantidad": 99}, cookies=headers)
        assert res.status_code == 200
        assert res.json()["stock_cantidad"] == 99

    def test_actualizar_stock_rol_stock(self, client: TestClient, session: Session, stock_user, producto_final):
        headers = get_auth_headers(session, stock_user)
        res = client.patch(f"{BASE}/{producto_final.id}/stock", json={"stock_cantidad": 30}, cookies=headers)
        assert res.status_code == 200

    def test_actualizar_stock_sin_permiso(self, client: TestClient, session: Session, client_user, producto_final):
        headers = get_auth_headers(session, client_user)
        res = client.patch(f"{BASE}/{producto_final.id}/stock", json={"stock_cantidad": 1}, cookies=headers)
        assert res.status_code == 403


class TestDisponibilidadProducto:
    def test_desactivar_producto(self, client: TestClient, session: Session, admin_user, producto_final):
        headers = get_auth_headers(session, admin_user)
        res = client.patch(f"{BASE}/{producto_final.id}/desactivar", cookies=headers)
        assert res.status_code == 200
        assert res.json()["disponible"] is False

    def test_activar_producto(self, client: TestClient, session: Session, admin_user, producto_final):
        headers = get_auth_headers(session, admin_user)
        client.patch(f"{BASE}/{producto_final.id}/desactivar", cookies=headers)
        res = client.patch(f"{BASE}/{producto_final.id}/activar", cookies=headers)
        assert res.status_code == 200
        assert res.json()["disponible"] is True


class TestEliminarProducto:
    def test_soft_delete_producto(self, client: TestClient, session: Session, admin_user, categoria_base, unidad_ud):
        headers = get_auth_headers(session, admin_user)
        res = client.post(BASE, json={
            "nombre": "A eliminar",
            "descripcion": "Test",
            "precio_base": 100.0,
            "es_producto_final": True,
            "stock_cantidad": 1,
            "categorias": [{"categoria_id": categoria_base.id, "es_principal": True}],
            "ingredientes": [],
        }, cookies=headers)
        prod_id = res.json()["id"]

        res = client.delete(f"{BASE}/{prod_id}", cookies=headers)
        assert res.status_code == 200

        res = client.get(f"{BASE}/{prod_id}")
        assert res.status_code == 404

    def test_eliminar_sin_permiso(self, client: TestClient, session: Session, client_user, producto_final):
        headers = get_auth_headers(session, client_user)
        res = client.delete(f"{BASE}/{producto_final.id}", cookies=headers)
        assert res.status_code == 403