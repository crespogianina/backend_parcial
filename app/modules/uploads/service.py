import re
from typing import Optional

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.modules.uploads.schemas import CloudinaryResponse

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


class UploadService:

    def _configure_cloudinary(self) -> None:
        if not all([
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        ]):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cloudinary no está configurado. Revise las variables CLOUDINARY_* en .env",
            )

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

    def _validate_image(self, file: UploadFile, content: bytes) -> None:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Tipo de archivo no permitido. "
                    f"Use uno de: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
                ),
            )

        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo está vacío",
            )

        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La imagen supera el tamaño máximo de 5 MB",
            )

    def upload_image(self, file: UploadFile) -> CloudinaryResponse:
        self._configure_cloudinary()
        content = file.file.read()
        self._validate_image(file, content)

        try:
            result = cloudinary.uploader.upload(
                content,
                folder="foodstore",
                resource_type="image",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al subir imagen a Cloudinary: {exc}",
            ) from exc

        return CloudinaryResponse(
            secure_url=result["secure_url"],
            public_id=result["public_id"],
            width=result["width"],
            height=result["height"],
            format=result["format"],
            resource_type=result["resource_type"],
        )

    @staticmethod
    def public_id_from_url(url: str) -> Optional[str]:
        if "res.cloudinary.com" not in url:
            return None

        parts = url.split("/upload/", maxsplit=1)
        if len(parts) < 2:
            return None

        path = re.sub(r"^v\d+/", "", parts[1])
        if "." in path.rsplit("/", maxsplit=1)[-1]:
            path = path.rsplit(".", maxsplit=1)[0]

        return path or None

    def _cloudinary_configured(self) -> bool:
        return all([
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        ])

    def delete_image_by_url(self, url: str) -> None:
        public_id = self.public_id_from_url(url)
        if not public_id or not self._cloudinary_configured():
            return

        try:
            self._configure_cloudinary()
            cloudinary.uploader.destroy(public_id, resource_type="image")
        except Exception:
            return

    def delete_images_by_urls(self, urls: list[str]) -> None:
        for url in urls:
            if url:
                self.delete_image_by_url(url)

    def delete_image(self, public_id: str) -> None:
        self._configure_cloudinary()

        try:
            result = cloudinary.uploader.destroy(public_id, resource_type="image")
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al eliminar imagen en Cloudinary: {exc}",
            ) from exc

        if result.get("result") != "ok":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Imagen no encontrada en Cloudinary",
            )
