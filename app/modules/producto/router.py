
from typing import Annotated, List

from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.producto.schemas import ProductoCreate, ProductoPublic,  ProductoUpdate, ProductoList
from app.modules.categoria.schemas import CategoriaPublic
from app.modules.ingrediente.schemas import IngredientePublic
from app.modules.producto.service import ProductoService

router = APIRouter()

def get_producto_service(session: Session = Depends(get_session)) -> ProductoService:
    return ProductoService(session)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=ProductoPublic, status_code=status.HTTP_201_CREATED, summary="Crear un producto")
def create_producto(data: ProductoCreate, svc: ProductoService = Depends(get_producto_service)) -> ProductoPublic:
    return svc.create(data)

@router.get("/", response_model=ProductoList, status_code=status.HTTP_200_OK, summary="Obtener todas los producto activos")
def get_producto_existentes(svc: ProductoService = Depends(get_producto_service), offset: Annotated[int, Query(ge=0)] = 0,limit: Annotated[int, Query(ge=1, le=50)] = 50) -> ProductoList:
    return svc.get_all(offset, limit)

@router.get("/{id}", response_model=ProductoPublic, status_code=status.HTTP_200_OK, summary="Obtener producto por id")
def get_producto_by_id(id: Annotated[int, Path(gt=0)], svc: ProductoService = Depends(get_producto_service)) -> ProductoPublic:
    return svc.get_by_id(id)

@router.put("/{id}", response_model=ProductoPublic, status_code=status.HTTP_200_OK, summary="Editar producto por id")
def edit_producto(id: Annotated[int, Path(gt=0)], producto: ProductoUpdate, svc: ProductoService = Depends(get_producto_service)) -> ProductoPublic:
    return svc.update(id, producto)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar producto por id")
def eliminar_producto(id: Annotated[int, Path(gt=0)], svc: ProductoService = Depends(get_producto_service)) -> None:
    return svc.soft_delete(id)

@router.get("/{id}/categorias", response_model=List[CategoriaPublic], status_code=status.HTTP_200_OK, summary="Obtener categorias de un producto")
def obtener_categorias_producto(id: Annotated[int, Path(gt=0)], svc: ProductoService = Depends(get_producto_service))-> List[CategoriaPublic]:
    return svc.obtener_categorias_producto(id)

@router.get("/{id}/ingredientes", response_model=List[IngredientePublic], status_code=status.HTTP_200_OK, summary="Obtener los ingredientes de un producto")
def obtener_ingredientess_producto(id: Annotated[int, Path(gt=0)], svc: ProductoService = Depends(get_producto_service)) -> List[IngredientePublic]:
    return svc.obtener_ingredientes_producto(id)

