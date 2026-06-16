import io
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.uploads.service import UploadService
from tests.conftest import clear_auth_cookie, set_auth_cookie

BASE = "/api/v1/uploads"

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)

MOCK_UPLOAD_RESULT = {
    "secure_url": "https://res.cloudinary.com/demo/image/upload/v1/foodstore/test.png",
    "public_id": "foodstore/test",
    "width": 800,
    "height": 600,
    "format": "png",
    "resource_type": "image",
}


def _png_file(name: str = "test.png") -> tuple[str, io.BytesIO, str]:
    return (name, io.BytesIO(PNG_1X1), "image/png")


class TestUploadImagen:

    @patch("app.modules.uploads.service.cloudinary.uploader.upload")
    def test_upload_exitoso(
        self, mock_upload, client: TestClient, session: Session, admin_user
    ):
        mock_upload.return_value = MOCK_UPLOAD_RESULT
        set_auth_cookie(client, session, admin_user)
        res = client.post(f"{BASE}/imagen", files={"file": _png_file()})
        clear_auth_cookie(client)

        assert res.status_code == 201
        body = res.json()
        assert body["secure_url"] == MOCK_UPLOAD_RESULT["secure_url"]
        assert body["public_id"] == MOCK_UPLOAD_RESULT["public_id"]
        assert body["width"] == 800
        assert body["format"] == "png"
        mock_upload.assert_called_once()

    def test_upload_sin_autenticar(self, client: TestClient):
        res = client.post(f"{BASE}/imagen", files={"file": _png_file()})
        assert res.status_code == 401

    def test_upload_sin_permiso(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.post(f"{BASE}/imagen", files={"file": _png_file()})
        clear_auth_cookie(client)
        assert res.status_code == 403

    def test_upload_tipo_invalido(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.post(
            f"{BASE}/imagen",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        clear_auth_cookie(client)
        assert res.status_code == 400
        assert "no permitido" in res.json()["detail"].lower()

    def test_upload_archivo_vacio(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.post(
            f"{BASE}/imagen",
            files={"file": ("vacio.png", io.BytesIO(b""), "image/png")},
        )
        clear_auth_cookie(client)
        assert res.status_code == 400
        assert "vacío" in res.json()["detail"].lower()

    def test_upload_archivo_muy_grande(self, client: TestClient, session: Session, admin_user):
        set_auth_cookie(client, session, admin_user)
        res = client.post(
            f"{BASE}/imagen",
            files={
                "file": (
                    "grande.png",
                    io.BytesIO(b"x" * (5 * 1024 * 1024 + 1)),
                    "image/png",
                )
            },
        )
        clear_auth_cookie(client)
        assert res.status_code == 400
        assert "5 mb" in res.json()["detail"].lower()

    @patch("app.modules.uploads.service.cloudinary.uploader.upload")
    def test_upload_error_cloudinary(
        self, mock_upload, client: TestClient, session: Session, admin_user
    ):
        mock_upload.side_effect = RuntimeError("Cloudinary caído")
        set_auth_cookie(client, session, admin_user)
        res = client.post(f"{BASE}/imagen", files={"file": _png_file()})
        clear_auth_cookie(client)
        assert res.status_code == 502
        assert "Cloudinary" in res.json()["detail"]

    def test_upload_cloudinary_no_configurado(
        self, monkeypatch, client: TestClient, session: Session, admin_user
    ):
        monkeypatch.setattr("app.modules.uploads.service.settings.CLOUDINARY_CLOUD_NAME", "")
        monkeypatch.setattr("app.modules.uploads.service.settings.CLOUDINARY_API_KEY", "")
        monkeypatch.setattr("app.modules.uploads.service.settings.CLOUDINARY_API_SECRET", "")
        set_auth_cookie(client, session, admin_user)
        res = client.post(f"{BASE}/imagen", files={"file": _png_file()})
        clear_auth_cookie(client)
        assert res.status_code == 503
        assert "Cloudinary" in res.json()["detail"]


class TestDeleteImagen:

    @patch("app.modules.uploads.service.cloudinary.uploader.destroy")
    def test_delete_exitoso(
        self, mock_destroy, client: TestClient, session: Session, admin_user
    ):
        mock_destroy.return_value = {"result": "ok"}
        set_auth_cookie(client, session, admin_user)
        res = client.delete(f"{BASE}/imagen/foodstore%2Ftest")
        clear_auth_cookie(client)
        assert res.status_code == 204
        mock_destroy.assert_called_once_with("foodstore/test", resource_type="image")

    def test_delete_sin_autenticar(self, client: TestClient):
        res = client.delete(f"{BASE}/imagen/foodstore%2Ftest")
        assert res.status_code == 401

    def test_delete_sin_permiso(self, client: TestClient, session: Session, client_user):
        set_auth_cookie(client, session, client_user)
        res = client.delete(f"{BASE}/imagen/foodstore%2Ftest")
        clear_auth_cookie(client)
        assert res.status_code == 403

    @patch("app.modules.uploads.service.cloudinary.uploader.destroy")
    def test_delete_imagen_no_encontrada(
        self, mock_destroy, client: TestClient, session: Session, admin_user
    ):
        mock_destroy.return_value = {"result": "not found"}
        set_auth_cookie(client, session, admin_user)
        res = client.delete(f"{BASE}/imagen/foodstore%2Finexistente")
        clear_auth_cookie(client)
        assert res.status_code == 404

    @patch("app.modules.uploads.service.cloudinary.uploader.destroy")
    def test_delete_error_cloudinary(
        self, mock_destroy, client: TestClient, session: Session, admin_user
    ):
        mock_destroy.side_effect = RuntimeError("Cloudinary caído")
        set_auth_cookie(client, session, admin_user)
        res = client.delete(f"{BASE}/imagen/foodstore%2Ftest")
        clear_auth_cookie(client)
        assert res.status_code == 502


class TestUploadServiceHelpers:

    def test_public_id_from_url_cloudinary(self):
        url = "https://res.cloudinary.com/demo/image/upload/v1234567890/foodstore/producto_1.png"
        assert UploadService.public_id_from_url(url) == "foodstore/producto_1"

    def test_public_id_from_url_invalida(self):
        assert UploadService.public_id_from_url("https://example.com/img.png") is None
