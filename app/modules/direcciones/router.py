from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.modules.direcciones.schemas import DireccionCreate, DireccionList, DireccionPublic, DireccionUpdate
from app.modules.direcciones.service import DireccionService
from app.modules.usuarios.schemas import UserPublic

router = APIRouter(dependencies=[Depends(get_current_active_user)])


def get_direccion_service(session: Session = Depends(get_session)) -> DireccionService:
    return DireccionService(session)


@router.post("/", response_model=DireccionPublic, status_code=status.HTTP_201_CREATED, summary="Crear dirección de entrega")
def create_direccion(
    data: DireccionCreate,
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    svc: DireccionService = Depends(get_direccion_service),
) -> DireccionPublic:
    return svc.create(current_user, data)


@router.get("/", response_model=DireccionList, status_code=status.HTTP_200_OK, summary="Listar direcciones del usuario autenticado")
def list_direcciones(
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    svc: DireccionService = Depends(get_direccion_service),
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
) -> DireccionList:
    return svc.list_all(current_user, offset=offset, limit=limit)


@router.get("/{id}", response_model=DireccionPublic, status_code=status.HTTP_200_OK, summary="Obtener dirección por id")
def get_direccion(
    id: Annotated[int, Path(gt=0)],
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    svc: DireccionService = Depends(get_direccion_service),
) -> DireccionPublic:
    return svc.get_by_id(current_user, id)


@router.put("/{id}", response_model=DireccionPublic, status_code=status.HTTP_200_OK, summary="Editar dirección por id")
def update_direccion(
    id: Annotated[int, Path(gt=0)],
    data: DireccionUpdate,
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    svc: DireccionService = Depends(get_direccion_service),
) -> DireccionPublic:
    return svc.update(current_user, id, data)


@router.delete("/{id}", status_code=status.HTTP_200_OK, summary="Eliminar dirección (soft delete)")
def delete_direccion(
    id: Annotated[int, Path(gt=0)],
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    svc: DireccionService = Depends(get_direccion_service),
) -> dict:
    svc.soft_delete(current_user, id)
    return {"mensaje": f"Se eliminó correctamente la dirección con id {id}"}


@router.patch("/{id}/principal", response_model=DireccionPublic, status_code=status.HTTP_200_OK, summary="Marcar dirección como principal")
def set_direccion_principal(
    id: Annotated[int, Path(gt=0)],
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    svc: DireccionService = Depends(get_direccion_service),
) -> DireccionPublic:
    return svc.set_principal(current_user, id)
