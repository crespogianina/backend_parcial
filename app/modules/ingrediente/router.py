
from typing import Annotated, List, Optional      

from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.ingrediente.schemas import IngredienteCreate, IngredientePublic,  IngredienteUpdate, IngredienteList
from app.modules.ingrediente.service import IngredienteService

router = APIRouter()

def get_ingrediente_service(session: Session = Depends(get_session)) -> IngredienteService:
    return IngredienteService(session)

#Endpoints

@router.post("/", response_model=IngredientePublic, status_code=status.HTTP_201_CREATED, summary="Crear un ingrediente")
def create_ingrediente(data: IngredienteCreate, svc: IngredienteService = Depends(get_ingrediente_service)) -> IngredientePublic:
    return svc.create(data)

@router.get("/", response_model=IngredienteList, status_code=status.HTTP_200_OK, summary="Obtener todos los ingredientes activos")
def get_ingredientes_existentes(svc: IngredienteService = Depends(get_ingrediente_service),offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=50)] = 50, es_alergeno: Annotated[Optional[bool], Query()] = None) -> IngredienteList:
    return svc.get_all(es_alergeno,offset, limit )

@router.get("/alergenos", response_model=IngredienteList, status_code=status.HTTP_200_OK, summary="Obtener todos los ingredientes alérgenos")
def get_ingredientes_alergenos(
    svc: IngredienteService = Depends(get_ingrediente_service),
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 50
) -> IngredienteList:
    return svc.get_alergenos(offset, limit)

@router.get("/{id}", response_model=IngredientePublic, status_code=status.HTTP_200_OK, summary="Obtener ingrediente por id")
def get_ingrediente_by_id(id: Annotated[int, Path(gt=0)], svc: IngredienteService = Depends(get_ingrediente_service)) -> IngredientePublic:
    return svc.get_by_id(id)

@router.put("/{id}", response_model=IngredientePublic, status_code=status.HTTP_200_OK, summary="Editar ingrediente por id")
def edit_ingrediente(id: Annotated[int, Path(gt=0)], ingrediente: IngredienteUpdate, svc: IngredienteService = Depends(get_ingrediente_service)) -> IngredientePublic:
    return svc.update(id, ingrediente)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar ingrediente por id")
def eliminar_ingrediente(id: Annotated[int, Path(gt=0)], svc: IngredienteService = Depends(get_ingrediente_service)) -> None:
    return svc.soft_delete(id)

