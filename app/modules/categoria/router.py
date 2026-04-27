
from typing import Annotated, List

from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.categoria.schemas import CategoriaCreate, CategoriaPublic, CategoriaTreeRead, CategoriaUpdate, CategoriaList
from app.modules.categoria.service import CategoriaService

router = APIRouter()

def get_categoria_service(session: Session = Depends(get_session)) -> CategoriaService:
    return CategoriaService(session)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=CategoriaPublic, status_code=status.HTTP_201_CREATED, summary="Crear una categoria")
def create_categoria(data: CategoriaCreate, svc: CategoriaService = Depends(get_categoria_service)) -> CategoriaPublic:
    return svc.create(data)

@router.get("/", response_model=CategoriaList, status_code=status.HTTP_200_OK, summary="Obtener todas las categorias activas")
def get_categorias_existentes(svc: CategoriaService = Depends(get_categoria_service), offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=50)] = 50) -> CategoriaList:
    return svc.get_all_active(offset, limit)

@router.get("/tree", response_model=List[CategoriaTreeRead], status_code=status.HTTP_200_OK, summary="Obtener todas las categorias y sus subcategorias")
def get_categorias_tree(
    svc: CategoriaService = Depends(get_categoria_service),) -> List[CategoriaTreeRead]:
    return svc.get_tree()

@router.get("/{id}", response_model=CategoriaPublic, status_code=status.HTTP_200_OK, summary="Obtener categoria por id")
def get_categoria_por_id(id: Annotated[int, Path(gt=0)], svc: CategoriaService = Depends(get_categoria_service)) -> CategoriaPublic:
    return svc.get_by_id(id)

@router.put("/{id}", response_model=CategoriaPublic, status_code=status.HTTP_200_OK, summary="Editar categoria por id")
def edit_categoria(id: Annotated[int, Path(gt=0)], categoria: CategoriaUpdate, svc: CategoriaService = Depends(get_categoria_service)) -> CategoriaPublic:
    return svc.update(id, categoria)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar categoria por id")
def eliminar_categoria(id: Annotated[int, Path(gt=0)], svc: CategoriaService = Depends(get_categoria_service)) -> None:
    return svc.soft_delete(id)

