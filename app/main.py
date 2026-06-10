from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import create_db_and_tables
from app.modules.producto.router import router as producto_router
from app.modules.categoria.router import router as categoria_router
from app.modules.ingrediente.router import router as ingrediente_router
from app.modules.usuarios.router import router as usuario_router
from app.modules.direcciones.router import router as direccion_router
from app.modules.pedido.router import router as pedido_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        create_db_and_tables()
    except Exception:
        pass
    yield


app = FastAPI(
    title="Integrador",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(usuario_router, prefix="/usuario", tags=["usuarios"])
api_v1.include_router(categoria_router, prefix="/categorias", tags=["categorias"])
api_v1.include_router(ingrediente_router, prefix="/ingredientes", tags=["ingredientes"])
api_v1.include_router(producto_router, prefix="/productos", tags=["productos"])
api_v1.include_router(direccion_router, prefix="/direcciones", tags=["direcciones"])
api_v1.include_router(pedido_router, prefix="/pedidos", tags=["pedidos"])

app.include_router(api_v1)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(content=b"", media_type="image/x-icon")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/debug/ws-rooms", tags=["debug"])
def ws_rooms():
    from app.core.websocket import manager
    return {
        "total_connections": manager.get_active_connections_count(),
        "rooms": manager.get_rooms_info(),
    }