
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel import Session
from app.core.database import get_session
from app.core.deps import require_role
from app.modules.producto.schemas import IngredienteAsignar, ProductoCreate, ProductoPublic,  ProductoUpdate, ProductoList
from app.modules.categoria.schemas import CategoriaPublic
from app.modules.ingrediente.schemas import IngredientePublic
from app.modules.producto.service import ProductoService
from app.modules.usuarios.schemas import UserPublic

router = APIRouter()

def get_producto_service(session: Session = Depends(get_session)) -> ProductoService:
    return ProductoService(session)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=ProductoList, status_code=status.HTTP_200_OK, summary="Obtener todos los productos")
def get_all_productos(
    nombre: Annotated[Optional[str], Query(description="Búsqueda por texto en nombre")] = None,
    descripcion: Annotated[Optional[str], Query(description="Búsqueda por texto en descripción")] = None,
    disponible: Annotated[Optional[bool], Query(description="Filtrar por disponibilidad")] = None,
    categoria_id: Annotated[Optional[int], Query(description="Filtrar por categoría")] = None,
    svc: ProductoService = Depends(get_producto_service), 
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 50
) -> ProductoList:
    return svc.get_all_productos(nombre, descripcion, disponible, categoria_id, offset, limit)


@router.get("/{id}", response_model=ProductoPublic, status_code=status.HTTP_200_OK, summary="Obtener producto por id")
def get_producto_by_id(id: Annotated[int, Path(gt=0)], svc: ProductoService = Depends(get_producto_service)) -> ProductoPublic:
    return svc.get_by_id(id)


@router.post("/", response_model=ProductoPublic, status_code=status.HTTP_201_CREATED, summary="Crear un producto")
def create_producto(
    data: ProductoCreate, 
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))], 
    svc: ProductoService = Depends(get_producto_service)
) -> ProductoPublic:
    return svc.create(data)


@router.put("/{id}", response_model=ProductoPublic, status_code=status.HTTP_200_OK, summary="Editar producto por id")
def edit_producto(
    id: Annotated[int, Path(gt=0)],
    producto: ProductoUpdate,               
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))], 
    svc: ProductoService = Depends(get_producto_service)
) -> ProductoPublic:
    return svc.update(id, producto)

# Consulta
# Aparece solo un endpoint /disponibilidad cambiar disponible true o false
@router.patch(
    "/{id}/desactivar",
    response_model=ProductoPublic,
    status_code=status.HTTP_200_OK,
    summary="Activar o desactivar disponibilidad (ADMIN y STOCK)",
)
def desactivar_producto(
    id: Annotated[int, Path(gt=0)],
    _user: Annotated[UserPublic, Depends(require_role(["ADMIN", "STOCK"]))],
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.update_disponibilidad(id, False)


# Consulta
# Aparece solo un endpoint /disponibilidad cambiar disponible true o false
@router.patch(
    "/{id}/activar",
    response_model=ProductoPublic,
    status_code=status.HTTP_200_OK,
    summary="Activar o desactivar disponibilidad (ADMIN y STOCK)",
)
def activar_producto(
    id: Annotated[int, Path(gt=0)],
    _user: Annotated[UserPublic, Depends(require_role(["ADMIN", "STOCK"]))],
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.update_disponibilidad(id, True)


@router.patch(
    "/{id}/imagenes",
    response_model=ProductoPublic,
    status_code=status.HTTP_200_OK,
    summary="Actualizar lista imagenes (ADMIN)",
)
def actualizar_imagenes(
    id: Annotated[int, Path(gt=0)],
    imagenes: List[str],
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.actualizar_imagenes(id, imagenes)


@router.delete("/{id}", status_code=status.HTTP_200_OK, summary="Eliminar producto por id (Soft Delete)")
def eliminar_producto(
    id: Annotated[int, Path(gt=0)],
    _user: Annotated[UserPublic, Depends(require_role(["ADMIN", "STOCK"]))], 
    svc: ProductoService = Depends(get_producto_service),
) -> dict:
    svc.soft_delete(id)
    return {"mensaje": f"Se elimino correctamente el producto con id {id}"} 


@router.get("/{id}/ingredientes", response_model=List[IngredientePublic], status_code=status.HTTP_200_OK, summary="Obtener los ingredientes de un producto")
def obtener_ingredientess_producto(id: Annotated[int, Path(gt=0)], svc: ProductoService = Depends(get_producto_service)) -> List[IngredientePublic]:
    return svc.obtener_ingredientes_producto(id)


@router.post(
    "/{id}/ingredientes",
    response_model=ProductoPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Asociar un ingrediente al producto con cantidad y unidad (ADMIN)",
)
def asociar_ingrediente_producto(
    id: Annotated[int, Path(gt=0)],
    data: IngredienteAsignar,
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))],
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.asociar_ingrediente(id, data)


@router.get("/{id}/categorias", response_model=List[CategoriaPublic], status_code=status.HTTP_200_OK, summary="Obtener categorias de un producto")
def obtener_categorias_producto(id: Annotated[int, Path(gt=0)], svc: ProductoService = Depends(get_producto_service))-> List[CategoriaPublic]:
    return svc.obtener_categorias_producto(id)