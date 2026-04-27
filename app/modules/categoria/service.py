from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlmodel import Session
from .unit_of_work import CategoriaUnitOfWork
from .models import Categoria
from .schemas import CategoriaCreate, CategoriaTreeRead, CategoriaUpdate, CategoriaPublic, CategoriaList

class CategoriaService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────
    def _get_or_404(self, uow: CategoriaUnitOfWork, categoria_id: int) -> Categoria:
        categoria = uow.categorias.get_by_id(categoria_id)

        if not categoria:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoria con id={categoria_id} no encontrado",
            )
        
        if categoria.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La categoria con id={categoria_id} fue borrada",
            )
        
        return categoria

    def _assert_nombre_unique(self, uow: CategoriaUnitOfWork, nombre: str) -> None:
        if uow.categorias.get_by_name(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El nombre '{nombre}' ya está en uso",
            )    

    def validate_parent_id_different(self, parent_id: Optional[int], categoria_id: int):
        if parent_id is not None and parent_id == categoria_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Una categia no puede ser padre de si misma"
            )

    def _validate_no_active_children(self, categoria: Categoria) -> None:
        hijos_activos = [
            hijo for hijo in categoria.hijos
            if hijo.deleted_at is None
        ]

        if hijos_activos:
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar una categoría que tiene subcategorias activas"
            )
        
    # ── Casos de uso ─────────────────────────────────────────────────────────

    def create(self, data: CategoriaCreate) -> CategoriaPublic: 
        with CategoriaUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)

            categoria = Categoria.model_validate(data)
            uow.categorias.add(categoria)
            result = CategoriaPublic.model_validate(categoria) 

        return result

    def get_all_active(self, offset: int = 0, limit: int = 20) -> CategoriaList:
        with CategoriaUnitOfWork(self._session) as uow:
            categorias = uow.categorias.get_categorias_existentes(offset=offset, limit=limit)
            total = uow.categorias.count_categorias_existentes()

            result = CategoriaList(data=[CategoriaPublic.model_validate(c) for c in categorias],total=total)
            
        return result

    def get_by_id(self, categoria_id: int) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)
            result = CategoriaPublic.model_validate(categoria)

        return result

    def update(self, categoria_id: int, data: CategoriaUpdate) -> CategoriaPublic: 
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)

            if data.parent_id is not None:
                self._get_or_404(uow, data.parent_id)
                self.validate_parent_id_different(data.parent_id, categoria_id)

            if data.nombre and data.nombre != categoria.nombre:
                self._assert_nombre_unique(uow, data.nombre)
            
            patch = data.model_dump(exclude_unset=True)

            for field, value in patch.items():
                setattr(categoria, field, value)

            categoria.updated_at = datetime.utcnow() 
            uow.categorias.add(categoria)
            result = CategoriaPublic.model_validate(categoria)

        return result


    def soft_delete(self, categoria_id: int) -> None:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)
            self._validate_no_active_children(categoria)
            
            categoria.deleted_at = datetime.utcnow()
            uow.categorias.add(categoria)


    def get_tree(self) -> List[CategoriaTreeRead]:
        with CategoriaUnitOfWork(self._session) as uow:
            categorias = uow.categorias.get_categoria_tree()

            categorias_dict = {}

            for categoria in categorias:
                categorias_dict[categoria.id] = {
                    "id": categoria.id,
                    "nombre": categoria.nombre,
                    "descripcion": categoria.descripcion,
                    "imagen_url": categoria.imagen_url,
                    "parent_id": categoria.parent_id,
                    "hijos": []
                }

            tree = []

            for categoria in categorias:
                item = categorias_dict[categoria.id]

                if categoria.parent_id is None:
                    tree.append(item)
                else:
                    parent = categorias_dict.get(categoria.parent_id)

                    if parent:
                        parent["hijos"].append(item)

            return tree