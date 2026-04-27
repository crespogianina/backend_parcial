from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import create_db_and_tables
from app.modules.producto.router import router as producto_router
from app.modules.categoria.router import router as categoria_router
from app.modules.ingrediente.router import router as ingrediente_router
from app.modules.producto_categoria.router import router as producto_categoria_router
from app.modules.producto_ingrediente.router import router as producto_ingrediente_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Integrador",
    lifespan=lifespan,
)

app.include_router(categoria_router, prefix="/categorias", tags=["categorias"])
app.include_router(ingrediente_router, prefix="/ingredientes", tags=["ingredientes"])
app.include_router(producto_router, prefix="/productos", tags=["productos"])
app.include_router(producto_categoria_router, prefix="/productos", tags=["producto-categorias"])
app.include_router(producto_ingrediente_router, prefix="/productos", tags=["producto-ingredientes"])
