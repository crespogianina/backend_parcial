from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.categoria.schemas import CategoriaPublic
from app.modules.producto.service import ProductoService

router = APIRouter()


def get_producto_service(session: Session = Depends(get_session)) -> ProductoService:
    return ProductoService(session)


@router.get(
    "/{id}/categorias",
    response_model=list[CategoriaPublic],
    status_code=status.HTTP_200_OK,
    summary="Obtener categorias de un producto",
)
def obtener_categorias_producto(
    svc: ProductoService = Depends(get_producto_service),
    id: int = Annotated[int, Path(gt=0)],
) -> list[CategoriaPublic]:
    return svc.obtener_categorias_producto(id)
