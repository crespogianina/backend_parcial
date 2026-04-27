# app/modules/productos/service.py
from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from sqlmodel import Session

from .models import Producto, ProductoCategoria, ProductoIngrediente
from .schemas import ProductoCreate, ProductoPublic, ProductoUpdate, ProductoList
from app.modules.categoria.schemas import CategoriaPublic
from app.modules.ingrediente.schemas import IngredientePublic
from .unit_of_work import ProductoUnitOfWork

class ProductoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: ProductoUnitOfWork, producto_id: int) -> Producto:
        producto = uow.productos.get_by_id(producto_id)

        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con id={producto_id} no encontrado",
            )

        if producto.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con id={producto_id} fue eliminado",
            )
            
        return producto

    def _assert_nombre_unique(self, uow: ProductoUnitOfWork, nombre: str) -> None:
        if uow.productos.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El nombre '{nombre}' ya está en uso",
            )

    def _validate_no_duplicate_ids(self, ids: list[int], entity_name: str) -> None:
        duplicated_ids = {item_id for item_id in ids if ids.count(item_id) > 1}

        if duplicated_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se permiten {entity_name} duplicados: {list(duplicated_ids)}"
            )

    def _validar_categorias_existen(self, uow: ProductoUnitOfWork, categorias: list[int]) -> None:
        for cat in categorias:
                categoria = uow.categorias.get_by_id(cat)
                if not categoria or categoria.deleted_at is not None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Categoria {cat} no encontrada",
                    )

    def _validar_ingredientes_existen(self, uow: ProductoUnitOfWork, ingredientes: List[int]) -> None:
        for ing in ingredientes:
            ingrediente = uow.ingredientes.get_by_id(ing)
            if not ingrediente or ingrediente.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ingrediente {ing} no encontrado",
                )

    def _reemplazar_categorias(self, uow: ProductoUnitOfWork, producto_id: int, categoria_ids: list[int]) -> None:
        uow.productos.delete_categorias_by_producto(producto_id)

        for categoria_id in categoria_ids:
            link = ProductoCategoria(
                producto_id=producto_id,
                categoria_id=categoria_id,
                es_principal=False,
            )
            uow.productos.add(link)


    def _reemplazar_ingredientes(self, uow: ProductoUnitOfWork, producto_id: int, ingrediente_ids: list[int]) -> None:
        uow.productos.delete_ingredientes_by_producto(producto_id)

        for ingrediente_id in ingrediente_ids:
            link = ProductoIngrediente(
                producto_id=producto_id,
                ingrediente_id=ingrediente_id,
                es_removible=False,
            )
            uow.productos.add(link)                
                
    # ── Casos de uso ─────────────────────────────────────────────────────────

    def create(self, data: ProductoCreate) -> ProductoPublic:
        categoria_ids = [c.categoria_id for c in data.categorias]
        ingrediente_ids = [i.ingrediente_id for i in data.ingredientes]

        self._validate_no_duplicate_ids(categoria_ids, "categorías")

        if ingrediente_ids:
            self._validate_no_duplicate_ids(ingrediente_ids, "ingredientes")

        with ProductoUnitOfWork(self._session) as uow:
            self._validar_categorias_existen(uow,categoria_ids) 

            if ingrediente_ids:
                self._validar_ingredientes_existen(uow, ingrediente_ids)

            self._assert_nombre_unique(uow, data.nombre)

            producto = Producto.model_validate(data.model_dump(exclude={"categorias", "ingredientes"}))
            uow.productos.add(producto)
            self._session.flush()  

            for cat in data.categorias:
                link = ProductoCategoria(
                    producto_id=producto.id,
                    categoria_id=cat.categoria_id,
                    es_principal=cat.es_principal,
                )
                uow.productos.add(link)

            for ing in (data.ingredientes or []):
                link = ProductoIngrediente(
                    producto_id=producto.id,
                    ingrediente_id=ing.ingrediente_id,
                    es_removible=ing.es_removible,
                )
                uow.productos.add(link)

            result = ProductoPublic.model_validate(producto)

        return result

    def get_all(self, offset: int = 0, limit: int = 20) -> ProductoList:
        with ProductoUnitOfWork(self._session) as uow:
            productos = uow.productos.get_productos_existentes(offset=offset, limit=limit)
            total = uow.productos.count_productos_existentes()

            result = ProductoList(
                data=[ProductoPublic.model_validate(h) for h in productos],
                total=total,
            )
            
        return result

    def get_by_id(self, producto_id: int) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            result = ProductoPublic.model_validate(producto)

        return result

    def update(self, producto_id: int, data: ProductoUpdate) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            if data.nombre and data.nombre != producto.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            patch = data.model_dump(exclude_unset=True, exclude={"categorias", "ingredientes"})

            for field, value in patch.items():
                setattr(producto, field, value)

            if data.categorias is not None:
                categoria_ids = [cat.categoria_id for cat in data.categorias]

                self._validate_no_duplicate_ids(categoria_ids, "categorías")
                self._validar_categorias_existen(uow, categoria_ids)

                uow.productos.delete_categorias_by_producto(producto_id)

                for cat in data.categorias:
                    link = ProductoCategoria(
                        producto_id=producto_id,
                        categoria_id=cat.categoria_id,
                        es_principal=cat.es_principal,
                    )
                    uow.productos.add(link)

            if data.ingredientes is not None:
                ingrediente_ids = [ing.ingrediente_id for ing in data.ingredientes]

                self._validate_no_duplicate_ids(ingrediente_ids, "ingredientes")
                self._validar_ingredientes_existen(uow, ingrediente_ids)

                uow.productos.delete_ingredientes_by_producto(producto_id)

                for ing in data.ingredientes:
                    link = ProductoIngrediente(
                        producto_id=producto_id,
                        ingrediente_id=ing.ingrediente_id,
                        es_removible=ing.es_removible,
                    )
                    uow.productos.add(link)

            producto.updated_at = datetime.utcnow()
            uow.productos.add(producto)
            result = ProductoPublic.model_validate(producto)

        return result
    
    def soft_delete(self, producto_id: int) -> None:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            producto.deleted_at = datetime.utcnow()
            uow.productos.add(producto)

    def obtener_categorias_producto(self, producto_id: int) -> List[CategoriaPublic]:
        with ProductoUnitOfWork(self._session) as uow:
            self._get_or_404(uow, producto_id)
            categorias = uow.productos.get_categorias_by_producto(producto_id)

            return [CategoriaPublic.model_validate(categoria)for categoria in categorias]

    def obtener_ingredientes_producto(self, producto_id: int) -> List[IngredientePublic]:
        with ProductoUnitOfWork(self._session) as uow:
            self._get_or_404(uow, producto_id)
            ingredientes = uow.productos.get_ingredientes_by_producto(producto_id)

            return [IngredientePublic.model_validate(ingrediente)for ingrediente in ingredientes]