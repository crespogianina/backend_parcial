from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.exceptions.exception_handlers import register_exception_handlers
from app.core.logger import get_logger, setup_logging
from app.core.middleware.logging_middleware import LoggingMiddleware
from app.core.middleware.timing_middleware import TimingMiddleware
from app.modules.categoria.router import router as categoria_router
from app.modules.direcciones.router import router as direccion_router
from app.modules.estadisticas.router import router as estadisticas_router
from app.modules.ingrediente.router import router as ingrediente_router
from app.modules.pago.router import router as pago_router
from app.modules.pedido.router import router as pedido_router
from app.modules.producto.router import router as producto_router
from app.modules.uploads.router import router as uploads_router
from app.modules.usuarios.router import router as usuario_router

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app.startup")
    try:
        create_db_and_tables()
    except Exception as e:
        logger.warning("db init failed: %s", e)
    yield
    logger.info("app.shutdown")


app = FastAPI(
    title="Integrador",
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

# Orden importa: primero los custom, CORS al final
app.add_middleware(LoggingMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
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
api_v1.include_router(uploads_router, prefix="/uploads", tags=["uploads"])
api_v1.include_router(pago_router, prefix="/pagos", tags=["pagos"])
api_v1.include_router(estadisticas_router, prefix="/estadisticas", tags=["estadisticas"])

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
