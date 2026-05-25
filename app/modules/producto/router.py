
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel import Session
from app.core.database import get_session
from app.core.deps import get_current_active_user, require_role
from app.modules.producto.schemas import ProductoCreate, ProductoPublic,  ProductoUpdate, ProductoList
from app.modules.categoria.schemas import CategoriaPublic
from app.modules.ingrediente.schemas import IngredientePublic
from app.modules.producto.service import ProductoService
from app.modules.usuarios.schemas import UserPublic

router = APIRouter(dependencies=[Depends(get_current_active_user)])

def get_producto_service(session: Session = Depends(get_session)) -> ProductoService:
    return ProductoService(session)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=ProductoPublic, status_code=status.HTTP_201_CREATED, summary="Crear un producto")
def create_producto(
    data: ProductoCreate, 
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))], 
    svc: ProductoService = Depends(get_producto_service)
) -> ProductoPublic:
    return svc.create(data)


@router.get("/", response_model=ProductoList, status_code=status.HTTP_200_OK, summary="Obtener todas los productos")
def get_all_productos(
    nombre: Annotated[Optional[str], Query()] = None,
    descripcion: Annotated[Optional[str], Query()] = None,
    disponible: Annotated[Optional[bool], Query()] = None,
    svc: ProductoService = Depends(get_producto_service), 
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 50
) -> ProductoList:
    return svc.get_all_productos(nombre, descripcion, disponible, offset, limit)


@router.get("/{id}", response_model=ProductoPublic, status_code=status.HTTP_200_OK, summary="Obtener producto por id")
def get_producto_by_id(id: Annotated[int, Path(gt=0)], svc: ProductoService = Depends(get_producto_service)) -> ProductoPublic:
    return svc.get_by_id(id)


@router.put("/{id}", response_model=ProductoPublic, status_code=status.HTTP_200_OK, summary="Editar producto por id")
def edit_producto(
    id: Annotated[int, Path(gt=0)],
    producto: ProductoUpdate,               
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))], 
    svc: ProductoService = Depends(get_producto_service)
) -> ProductoPublic:
    return svc.update(id, producto)


@router.delete("/{id}", status_code=status.HTTP_200_OK, summary="Eliminar producto por id")
def eliminar_producto(
    id: Annotated[int, Path(gt=0)],
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))], 
    svc: ProductoService = Depends(get_producto_service),
) -> dict:
    svc.soft_delete(id)
    return {"mensaje": f"Se elimino correctamente el producto con id {id}"} 


@router.post("/{id}", status_code=status.HTTP_200_OK, summary="Activar producto por id")
def activar_producto(
    id: Annotated[int, Path(gt=0)], 
    _admin: Annotated[UserPublic, Depends(require_role(["ADMIN"]))], 
    svc: ProductoService = Depends(get_producto_service)
) -> dict:
    svc.activar_producto(id)
    return {"mensaje": f"Se activo correctamente el producto con id {id}"} 


@router.get("/{id}/categorias", response_model=List[CategoriaPublic], status_code=status.HTTP_200_OK, summary="Obtener categorias de un producto")
def obtener_categorias_producto(id: Annotated[int, Path(gt=0)], svc: ProductoService = Depends(get_producto_service))-> List[CategoriaPublic]:
    return svc.obtener_categorias_producto(id)


@router.get("/{id}/ingredientes", response_model=List[IngredientePublic], status_code=status.HTTP_200_OK, summary="Obtener los ingredientes de un producto")
def obtener_ingredientess_producto(id: Annotated[int, Path(gt=0)], svc: ProductoService = Depends(get_producto_service)) -> List[IngredientePublic]:
    return svc.obtener_ingredientes_producto(id)

