import logging
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.core.deps import require_role
from app.modules.pago.schemas import (
    CrearPagoRequest,
    ConfirmarPagoRequest,
    PagoCrearResponse,
    PagoEstadoResponse,
)
from app.modules.pago.service import PagoService
from app.modules.usuarios.schemas import UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pagos", tags=["pagos"])

# ── Dependencias ──────────────────────────────────────────────────────────────

def get_payment_service(session: Session = Depends(get_session)) -> PagoService:
    return PagoService(session)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/create-preference", response_model=PagoCrearResponse)
def create_preference(
    data: CrearPagoRequest,
    usuario: Annotated[UserPublic, Depends(require_role(["CLIENT"]))],
    svc: PagoService = Depends(get_payment_service),
):
    return svc.crear_pago(data.pedido_id, usuario) 


@router.post("/webhook")
async def webhook(request: Request,svc: PagoService = Depends(get_payment_service)):
    try:
        query_params = dict(request.query_params)

        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()

        else:
            data = dict(await request.form())

        return await svc.procesar_webhook(data, query_params=query_params)
    except Exception as e:
        logger.exception("Error en webhook MP")
        return {"status": "error", "reason": str(e)}


@router.post("/confirm", response_model=PagoEstadoResponse)
async def confirm_payment(
    data: ConfirmarPagoRequest,
    usuario: Annotated[UserPublic, Depends(require_role(["CLIENT", "ADMIN", "PEDIDOS"]))],
    svc: PagoService = Depends(get_payment_service),
):
    return await svc.confirmar_pago(data.pedido_id, data.payment_id, usuario)


@router.get("/redirect/{pedido_id}/{status}")
async def redirect_after_pago(pedido_id: int, status: str, request: Request):
    frontend_url = settings.VITE_FRONTEND_URL or "http://localhost:5173"

    qs = request.url.query

    url = f"{frontend_url}/orders/{pedido_id}/{status}"

    if qs:
        url += f"?{qs}"
        
    return RedirectResponse(url=url)