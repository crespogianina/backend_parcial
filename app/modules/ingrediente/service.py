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
        
        
    def validate_unidad_medida(self, unidad_medida_id: int, uow: IngredienteUnitOfWork) -> None:
        unidad_medida = uow.productos.get_unidad_medida(unidad_medida_id)

        if not unidad_medida:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontro ninguna unidad de medida con ese id {unidad_medida_id}"
            )


    def actualizar_productos_stock(self, uow: IngredienteUnitOfWork, ingrediente_id: int) -> None:
        relaciones = uow.ingredientes.obtener_productos_asociados(ingrediente_id)
        productos_afectados = {r.producto_id for r in relaciones}

        for producto_id in productos_afectados:
            relaciones_producto = uow.ingredientes.get_ingredientes_de_producto(producto_id)

            unidades_posibles = []

            for pi in relaciones_producto:
                ingrediente = uow.ingredientes.get_by_id(pi.ingrediente_id)

                if not ingrediente or pi.cantidad <= 0:
                    continue

                unidades = int(ingrediente.stock_cantidad / pi.cantidad)
                unidades_posibles.append(unidades)

            nuevo_stock = min(unidades_posibles) if unidades_posibles else 0
            uow.ingredientes.actualizar_stock_producto(producto_id, nuevo_stock)

    # ─────────────────────────────────────────────────────────

    def create_ingrediente(self, data: IngredienteCreate) -> IngredientePublic: 
        with IngredienteUnitOfWork(self._session) as uow:
            self.validate_unidad_medida(data.unidad_medida_id, uow )
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
            stock_anterior = ingrediente.stock_cantidad

            for field, value in patch.items():
                setattr(ingrediente, field, value)

            ingrediente.updated_at = datetime.utcnow()
            uow.ingredientes.add(ingrediente)
            self._session.flush()

            if data.stock_cantidad is not None and data.stock_cantidad != stock_anterior:
                self.actualizar_productos_stock(uow, ingrediente_id)

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
                    detail=f"El ingrediente de id:{ingrediente_id} ya se encuentra activado",
                )
            
            ingrediente.deleted_at = None
            uow.ingredientes.add(ingrediente)