from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlmodel import Session
from .models import Producto, ProductoCategoria, ProductoIngrediente
from .schemas import CategoriaAsignar, CategoriaProductoRead, IngredienteAsignar, IngredienteProductoRead, ProductoCreate, ProductoPublic, ProductoUpdate, ProductoList, UnidadMedidaProductoRead
from app.modules.categoria.schemas import CategoriaPublic
from app.modules.ingrediente.schemas import IngredientePublic
from .unit_of_work import ProductoUnitOfWork
from app.modules.uploads.service import UploadService

FACTORES = {
    ("kg", "g"): 1000,
    ("g", "kg"): 0.001,
    ("l", "ml"): 1000,
    ("ml", "l"): 0.001,
}

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


    def _validar_unidad_medida(self, uow: ProductoUnitOfWork, unidad_medida_id: int) -> None:
        if not uow.productos.get_unidad_medida(unidad_medida_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unidad de medida con id={unidad_medida_id} no encontrada",
            )
        

    def _validar_unidades_medida_ingredientes(self, uow: ProductoUnitOfWork, ingredientes: list[IngredienteAsignar]) -> None:
        for ing in ingredientes:
            self._validar_unidad_medida(uow, ing.unidad_medida_id)
            

    def _reemplazar_categorias(self, uow: ProductoUnitOfWork, producto_id: int, categorias: list[CategoriaAsignar]) -> None:
        uow.productos.delete_categorias_by_producto(producto_id)

        for cat in categorias:
            uow.productos.add(
                ProductoCategoria(
                    producto_id=producto_id,
                    categoria_id=cat.categoria_id,
                    es_principal=cat.es_principal,
                )
            )


    def _reemplazar_ingredientes(self, uow: ProductoUnitOfWork, producto_id: int, ingredientes: list[IngredienteAsignar]) -> None:
        uow.productos.delete_ingredientes_by_producto(producto_id)

        for ingrediente in ingredientes:
            uow.productos.add(
                ProductoIngrediente(
                    producto_id=producto_id,
                    ingrediente_id=ingrediente.ingrediente_id,
                    es_removible=ingrediente.es_removible,
                    unidad_medida_id=ingrediente.unidad_medida_id,
                    cantidad= ingrediente.cantidad
                )
            )


    def _convertir_unidad(self, cantidad, origen, destino):
        if origen == destino:
            return cantidad

        factor = FACTORES.get((origen, destino))

        if factor is None:
            raise ValueError(
                f"No existe conversión entre {origen} y {destino}"
            )

        return cantidad * factor


    def _calcular_stock(self, uow: ProductoUnitOfWork, ingredientes: list[IngredienteAsignar]) -> int:
        if not ingredientes:
            return 0

        unidades_posibles: list[int] = []

        for ing in ingredientes:
            ingrediente = uow.ingredientes.get_by_id(ing.ingrediente_id)

            if not ingrediente or ing.cantidad <= 0:
                continue

            if not ingrediente.unidad_medida:
                raise ValueError(
                    f"El ingrediente {ingrediente.nombre} no tiene unidad de medida asociada"
                )

            unidad_producto = uow.productos.get_unidad_medida(
                ing.unidad_medida_id
            )

            if not unidad_producto:
                raise ValueError(
                    f"Unidad de medida {ing.unidad_medida_id} no encontrada"
                )

            stock_convertido = self._convertir_unidad(
                Decimal(ingrediente.stock_cantidad),
                ingrediente.unidad_medida.simbolo,
                unidad_producto.simbolo
            )

            unidades = int(
                stock_convertido / ing.cantidad
            )

            unidades_posibles.append(unidades)

        return min(unidades_posibles)
    
    
    def _to_producto_public(self, producto: Producto) -> ProductoPublic:
        unidad_medida = (
            UnidadMedidaProductoRead.model_validate(producto.unidad_medida)
            if producto.unidad_medida
            else None
        )

        categorias = [
            CategoriaProductoRead(
                id=pc.categoria.id,
                nombre=pc.categoria.nombre,
                descripcion=pc.categoria.descripcion,
                es_principal=pc.es_principal,
            )
            for pc in producto.producto_categorias
        ]

        ingredientes = [
                    IngredienteProductoRead(
                        id=pi.ingrediente.id,
                        nombre=pi.ingrediente.nombre,
                        descripcion=pi.ingrediente.descripcion,
                        es_removible=pi.es_removible,
                        es_alergeno=pi.ingrediente.es_alergeno,
                        cantidad=pi.cantidad,
                        unidad_medida_id=pi.unidad_medida_id,
                    )
            for pi in producto.producto_ingredientes
        ]

        return ProductoPublic(
            **producto.model_dump(),
            activo=producto.deleted_at is None,
            unidad_medida=unidad_medida,
            categorias=categorias,
            ingredientes=ingredientes,
        )
    

    def _recalcular_stock_desde_links(self, producto: Producto) -> int:
        unidades_posibles = []

        for pi in producto.producto_ingredientes:
            if not pi.ingrediente or pi.cantidad <= 0:
                continue

            unidades = int(pi.ingrediente.stock_cantidad / pi.cantidad)
            unidades_posibles.append(unidades)

        return min(unidades_posibles) if unidades_posibles else 0

    def _stock_maximo_por_ingredientes(
        self, uow: ProductoUnitOfWork, producto_id: int
    ) -> Optional[int]:
        relaciones = uow.ingredientes.get_ingredientes_de_producto(producto_id)

        if not relaciones:
            return None

        unidades_posibles: list[int] = []

        for pi in relaciones:
            ingrediente = uow.ingredientes.get_by_id(pi.ingrediente_id)

            if not ingrediente or pi.cantidad <= 0:
                continue

            unidad_receta = uow.productos.get_unidad_medida(pi.unidad_medida_id)
            unidad_ingrediente = uow.productos.get_unidad_medida(
                ingrediente.unidad_medida_id
            )

            if not unidad_receta or not unidad_ingrediente:
                continue

            stock_convertido = self._convertir_unidad(
                Decimal(ingrediente.stock_cantidad),
                unidad_ingrediente.simbolo,
                unidad_receta.simbolo,
            )
            unidades_posibles.append(int(stock_convertido / pi.cantidad))

        return min(unidades_posibles) if unidades_posibles else 0

    # ── Casos de uso ─────────────────────────────────────────────────────────

    def create(self, data: ProductoCreate) -> ProductoPublic:
        categoria_ids = [c.categoria_id for c in data.categorias]
        ingrediente_ids = [i.ingrediente_id for i in data.ingredientes]

        self._validate_no_duplicate_ids(categoria_ids, "categorías")

        if ingrediente_ids:
            self._validate_no_duplicate_ids(ingrediente_ids, "ingredientes")

        with ProductoUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)

            if data.unidad_medida_id:
                self._validar_unidad_medida(uow, data.unidad_medida_id)

            self._validar_categorias_existen(uow, categoria_ids) 

            if ingrediente_ids:
                self._validar_ingredientes_existen(uow, ingrediente_ids)

            producto = Producto.model_validate(data.model_dump(exclude={"categorias", "ingredientes"}))
            producto.stock_cantidad = 0
            uow.productos.add(producto)
            self._session.flush()

            self._reemplazar_categorias(uow, producto.id, data.categorias)
            
            self._validar_unidades_medida_ingredientes(uow, data.ingredientes)

            if data.ingredientes:
                self._reemplazar_ingredientes(uow, producto.id, data.ingredientes)

            producto.stock_cantidad = self._calcular_stock(uow,data.ingredientes)

            result = self._to_producto_public(producto)
            uow.productos.add(producto)

        return result


    def get_all_productos(
            self, 
            nombre: Optional[str]= None, 
            descripcion: Optional[str]= None, 
            disponible: Optional[bool]= None, 
            categoria_id: Optional[int]= None, 
            offset: int = 0, 
            limit: int = 20
        ) -> ProductoList:
        with ProductoUnitOfWork(self._session) as uow:
            productos = uow.productos.get_all_productos(nombre, descripcion, disponible, categoria_id, offset=offset, limit=limit)
            total = uow.productos.count_all_productos(nombre, descripcion, disponible, categoria_id)

            result = ProductoList(
                data=[self._to_producto_public(p) for p in productos],
                total=total,
            )
            
        return result


    def get_by_id(self, producto_id: int) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            result = self._to_producto_public(producto)
        return result


    def update(self, producto_id: int, data: ProductoUpdate) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            if data.nombre and data.nombre != producto.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            if data.unidad_medida_id is not None:
                self._validar_unidad_medida(uow, data.unidad_medida_id)

            patch = data.model_dump(exclude_unset=True, exclude={"categorias", "ingredientes"})

            for field, value in patch.items():
                setattr(producto, field, value)

            if data.categorias is not None:
                categoria_ids = [cat.categoria_id for cat in data.categorias]

                self._validate_no_duplicate_ids(categoria_ids, "categorías")
                self._validar_categorias_existen(uow, categoria_ids)

                self._reemplazar_categorias(uow, producto.id, data.categorias)

            if data.ingredientes is not None:
                ingrediente_ids = [ing.ingrediente_id for ing in data.ingredientes]

                self._validate_no_duplicate_ids(ingrediente_ids, "ingredientes")
                self._validar_ingredientes_existen(uow, ingrediente_ids)

                self._reemplazar_ingredientes(uow, producto.id, data.ingredientes)
                
                producto.stock_cantidad = self._calcular_stock(uow, data.ingredientes)
            
            producto.updated_at = datetime.utcnow()
            uow.productos.add(producto)
            result = self._to_producto_public(producto)

        return result
    

    def soft_delete(self, producto_id: int) -> None:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            if producto.deleted_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El producto de id:{producto_id} ya se encuentra desactivado",
                )

            if producto.imagenes_url:
                UploadService().delete_images_by_urls(producto.imagenes_url)
                producto.imagenes_url = None

            producto.deleted_at = datetime.utcnow()
            uow.productos.add(producto)
    

    def update_stock_cantidad(self, producto_id: int, stock_cantidad: int) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            if stock_cantidad == producto.stock_cantidad:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El producto de id:{producto_id} ya tiene stock_cantidad={stock_cantidad}",
                )

            max_stock = self._stock_maximo_por_ingredientes(uow, producto_id)

            if max_stock is not None and stock_cantidad > max_stock:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"El stock no puede superar {max_stock} unidades según "
                        f"el stock actual de sus ingredientes."
                    ),
                )

            producto.stock_cantidad = stock_cantidad
            producto.updated_at = datetime.now(timezone.utc)
            uow.productos.add(producto)

            return self._to_producto_public(producto)


    def update_disponibilidad(self, producto_id: int, disponible: bool) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            producto = uow.productos.get_by_id(producto_id)

            if not producto:
                raise HTTPException(status_code=404, detail=f"Producto de id:{producto_id} no encontrado")

            if producto.deleted_at is not None:
                raise HTTPException(status_code=409, detail=f"El producto de id:{producto_id} se encuentra eliminado")


            if disponible == producto.disponible:
                estado = "disponible" if disponible else "no disponible"

                raise HTTPException(status_code=409, detail=f"El producto de id:{producto_id} ya se encuentra {estado}")
            
            producto.disponible = disponible
            uow.productos.add(producto)
            
            return self._to_producto_public(producto)


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
        
    def asociar_ingrediente(self, producto_id: int, data: IngredienteAsignar) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            self._validar_ingredientes_existen(uow, [data.ingrediente_id])
            self._validar_unidad_medida(uow, data.unidad_medida_id)

            ya_asociado = any(
                pi.ingrediente_id == data.ingrediente_id
                for pi in producto.producto_ingredientes
            )
            
            if ya_asociado:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El ingrediente {data.ingrediente_id} ya está asociado al producto {producto_id}",
                )

            uow.productos.add(
                ProductoIngrediente(
                    producto_id=producto_id,
                    ingrediente_id=data.ingrediente_id,
                    es_removible=data.es_removible,
                    unidad_medida_id=data.unidad_medida_id,
                    cantidad=data.cantidad,
                )
            )
            
            self._session.flush()            
            self._session.refresh(producto)

            producto.stock_cantidad = self._recalcular_stock_desde_links(producto)
            producto.updated_at = datetime.now(timezone.utc)
            uow.productos.add(producto)

            result = self._to_producto_public(producto)

        return result


    def actualizar_imagenes(self, producto_id: int, imagenes: List[str]) -> ProductoPublic:
        imagenes = [url.strip() for url in imagenes if url.strip()]

        if len(imagenes) != len(set(imagenes)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se permiten imágenes duplicadas",
            )

        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            producto.imagenes_url = imagenes
            producto.updated_at = datetime.now(timezone.utc)
            uow.productos.add(producto)

            result = self._to_producto_public(producto)

        return result
    

    def list_all_unidades_medida(self) -> list[UnidadMedidaProductoRead]:
        with ProductoUnitOfWork(self._session) as uow:
            unidades = uow.productos.get_all_unidad_medida()
            return [UnidadMedidaProductoRead.model_validate(u) for u in unidades]