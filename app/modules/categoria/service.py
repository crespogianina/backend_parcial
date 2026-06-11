from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlmodel import Session
from .unit_of_work import CategoriaUnitOfWork
from .models import Categoria
from .schemas import CategoriaCreate, CategoriaTreeRead, CategoriaUpdate, CategoriaPublic, CategoriaList
from app.modules.uploads.service import UploadService

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


    def _validate_no_ciclo(
        self, uow: CategoriaUnitOfWork, categoria_id: int, nuevo_parent_id: int
    ) -> None:
        if nuevo_parent_id == categoria_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Una categoría no puede ser padre de sí misma",
            )

        cursor_id = nuevo_parent_id
        visited = set()

        while cursor_id is not None:
            if cursor_id in visited:
                break

            if cursor_id == categoria_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede agregar como padre una categoría que es descendiente del nodo actual",
                )

            visited.add(cursor_id)
            parent = uow.categorias.get_by_id(cursor_id)

            cursor_id = parent.parent_id if parent else None


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
        
    # ─────────────────────────────────────────────────────────

    def create(self, data: CategoriaCreate) -> CategoriaPublic: 
        with CategoriaUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)
            self._get_or_404(uow, data.parent_id) if data.parent_id else None

            categoria = Categoria.model_validate(data)
            uow.categorias.add(categoria)
            result = CategoriaPublic(**categoria.model_dump(), activo=categoria.deleted_at is None) 

        return result


    def get_all_categorias(self, nombre: Optional[str] = None, descripcion: Optional[str] = None, parent_id: Optional[int] = None, offset: int = 0, limit: int = 20) -> CategoriaList:
        with CategoriaUnitOfWork(self._session) as uow:
            categorias = uow.categorias.get_all_categorias(nombre=nombre, descripcion=descripcion, parent_id=parent_id, offset=offset, limit=limit)
            total = uow.categorias.count_all_categorias(nombre=nombre, descripcion=descripcion, parent_id=parent_id)

            result = CategoriaList(
                data = [CategoriaPublic(**i.model_dump(), activo=i.deleted_at is None)
                        for i in categorias],
                total=total,
            )
            
        return result


    def get_by_id(self, categoria_id: int) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)
            result = CategoriaPublic(**categoria.model_dump(), activo=categoria.deleted_at is None)

        return result
    

    def update(self, categoria_id: int, data: CategoriaUpdate) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)

            if data.parent_id is not None:
                self._get_or_404(uow, data.parent_id)           
                self._validate_no_ciclo(uow, categoria_id, data.parent_id)

            if data.nombre and data.nombre != categoria.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(categoria, field, value)

            categoria.updated_at = datetime.now(timezone.utc)   
            uow.categorias.add(categoria)
            result = CategoriaPublic(**categoria.model_dump(), activo=categoria.deleted_at is None)

        return result


    def actualizar_imagen(self, categoria_id: int, imagen_url: Optional[str]) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)

            categoria.imagen_url = imagen_url.strip() if imagen_url and imagen_url.strip() else None
            categoria.updated_at = datetime.now(timezone.utc)
            uow.categorias.add(categoria)

            result = CategoriaPublic(**categoria.model_dump(), activo=categoria.deleted_at is None)

        return result


    def soft_delete(self, categoria_id: int) -> None:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = uow.categorias.get_by_id(categoria_id)

            if not categoria:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No se encotro una categoria con id:{categoria_id}",
                )

            if categoria.deleted_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La categoria con id:{categoria_id} ya se encuentra desactivada",
                )
                
            self._validate_no_active_children(categoria)

            if categoria.imagen_url:
                UploadService().delete_image_by_url(categoria.imagen_url)

            categoria.deleted_at = datetime.now(timezone.utc)
            uow.categorias.add(categoria)


    def activar_categoria(self, categoria_id: int) -> None:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = uow.categorias.get_by_id(categoria_id)

            if not categoria:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No se encotro una categoria con id:{categoria_id}",
                )
            
            if not categoria.deleted_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La categoria con id:{categoria_id} ya se encuentra activada",
                )
            
            categoria.deleted_at = None
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