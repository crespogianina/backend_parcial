from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, UploadFile, status

from app.core.deps import require_role
from app.modules.uploads.schemas import CloudinaryResponse
from app.modules.uploads.service import UploadService
from app.modules.usuarios.schemas import UserPublic

router = APIRouter()


def get_upload_service() -> UploadService:
    return UploadService()


@router.post(
    "/imagen",
    response_model=CloudinaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir imagen a Cloudinary",
)
def upload_imagen(
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    file: Annotated[UploadFile, File(description="Imagen a subir")],
    service: UploadService = Depends(get_upload_service),
) -> CloudinaryResponse:
    return service.upload_image(file)


@router.delete(
    "/imagen/{public_id:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar imagen de Cloudinary",
)
def delete_imagen(
    public_id: Annotated[str, Path(description="public_id de Cloudinary")],
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    service: UploadService = Depends(get_upload_service),
) -> None:
    service.delete_image(public_id)
