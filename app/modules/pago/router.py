import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.modules.payments.schemas import (
    CrearPagoRequest,
    ConfirmarPagoRequest,
    PagoCrearResponse,
    PagoEstadoResponse,
)
from app.modules.payments.service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pagos", tags=["pagos"])


def get_payment_service(session: Session = Depends(get_session)) -> PaymentService:
    return PaymentService(session)


@router.post("/create-preference", response_model=PagoCrearResponse)
def create_preference(
    data: CrearPagoRequest,
    svc: PaymentService = Depends(get_payment_service),
):
    return svc.crear_pago(data.pedido_id)


@router.post("/webhook")
async def webhook(
    request: Request,
    svc: PaymentService = Depends(get_payment_service),
):
    try:
        query_params = dict(request.query_params)
        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()
        else:
            data = dict(await request.form())
        return svc.procesar_webhook(data, query_params=query_params)
    except Exception as e:
        logger.exception("Error en webhook MP")
        return {"status": "error", "reason": str(e)}


@router.post("/confirm", response_model=PagoEstadoResponse)
def confirm_payment(
    data: ConfirmarPagoRequest,
    svc: PaymentService = Depends(get_payment_service),
):
    return svc.confirmar_pago(data.pedido_id, data.payment_id)


@router.get("/redirect/{pedido_id}/{status}")
async def redirect_after_pago(pedido_id: int, status: str, request: Request):
    frontend_url = settings.VITE_FRONTEND_URL or "http://localhost:5173"

    qs = request.url.query

    url = f"{frontend_url}/orders/{pedido_id}/{status}"

    if qs:
        url += f"?{qs}"
    return RedirectResponse(url=url)