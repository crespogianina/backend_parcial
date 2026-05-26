from datetime import datetime
from typing import Optional
from fastapi import HTTPException, status
from sqlmodel import Session
from .models import Ingrediente
from .schemas import IngredienteCreate, IngredienteUpdate, IngredientePublic, IngredienteList
from .unit_of_work import IngredienteUnitOfWork


class IngredienteService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: IngredienteUnitOfWork, ingrediente_id: int) -> Ingrediente:
        ingrediente = uow.ingredientes.get_by_id(ingrediente_id)

        if not ingrediente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingrediente con id={ingrediente_id} no encontrado",
            )
        
        if ingrediente.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingrediente con id={ingrediente_id} fue eliminado",
            )

        return ingrediente
    

    def _assert_nombre_unique(self, uow: IngredienteUnitOfWork, nombre: str) -> None:
        if uow.ingredientes.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El nombre '{nombre}' ya está en uso",
            )
        
        
    def _validate_no_productos_asociados(self, ingrediente: Ingrediente) -> None:
        if ingrediente.producto_ingredientes:
            raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un ingrediente asociado a productos"
            )

    # ─────────────────────────────────────────────────────────

    def create_ingrediente(self, data: IngredienteCreate) -> IngredientePublic: 
        with IngredienteUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)

            ingrediente = Ingrediente.model_validate(data)
            uow.ingredientes.add(ingrediente)

            result = IngredientePublic(**ingrediente.model_dump(), activo=ingrediente.deleted_at is None)

        return result



    def get_all(self, es_alergeno: bool, nombre: Optional[str] = None, descripcion: Optional[str] = None, offset: int = 0, limit: int = 20) -> IngredienteList:
        with IngredienteUnitOfWork(self._session) as uow:
            ingredientes = uow.ingredientes.get_all_ingredientes(nombre, descripcion, es_alergeno, offset=offset, limit=limit)
            total = uow.ingredientes.count_all_ingredientes(nombre, descripcion, es_alergeno)

            result = IngredienteList(
                data = [IngredientePublic(**i.model_dump(),activo=i.deleted_at is None)
                        for i in ingredientes],
                total=total,
            )
            
        return result


    def get_by_id(self, ingrediente_id: int) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)
            result = IngredientePublic(**ingrediente.model_dump(), activo=ingrediente.deleted_at is None)

        return result


    def update(self, ingrediente_id: int, data: IngredienteUpdate) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)

            if data.nombre and data.nombre != ingrediente.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            patch = data.model_dump(exclude_unset=True)

            for field, value in patch.items():
                setattr(ingrediente, field, value)

            ingrediente.updated_at = datetime.utcnow()
            uow.ingredientes.add(ingrediente)
            result = IngredientePublic(**ingrediente.model_dump(), activo=ingrediente.deleted_at is None)

        return result


    def soft_delete(self, ingrediente_id: int) -> None:
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            self._validate_no_productos_asociados(ingrediente)

            if ingrediente.deleted_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El ingrediente de id:{ingrediente_id} ya se encuentra desactivado",
                )

            ingrediente.deleted_at = datetime.utcnow()
            uow.ingredientes.add(ingrediente)


    def activar_ingrediente(self, ingrediente_id: int) -> None:
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = uow.ingredientes.get_by_id(ingrediente_id)

            if not ingrediente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No se encontro un ingrediente con el id {ingrediente_id}",
                )

            if not ingrediente.deleted_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El ingrediente de id:{id} ya se encuentra activado",
                )
            
            ingrediente.deleted_at = None
            uow.ingredientes.add(ingrediente)