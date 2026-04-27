from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.ingrediente.schemas import IngredientePublic
from app.modules.producto.service import ProductoService

router = APIRouter()


def get_producto_service(session: Session = Depends(get_session)) -> ProductoService:
    return ProductoService(session)


@router.get(
    "/{id}/ingredientes",
    response_model=list[IngredientePublic],
    status_code=status.HTTP_200_OK,
    summary="Obtener ingredientes de un producto",
)
def obtener_ingredientes_producto(
    svc: ProductoService = Depends(get_producto_service),
    id: int = Annotated[int, Path(gt=0)],
) -> list[IngredientePublic]:
    return svc.obtener_ingredientes_producto(id)
