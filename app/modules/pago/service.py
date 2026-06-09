import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

ESTADO_MAP = {
    "approved":    "aprobado",
    "rejected":    "rechazado",
    "cancelled":   "rechazado",
    "refunded":    "rechazado",
    "charged_back":"rechazado",
    "pending":     "pendiente",
    "in_process":  "pendiente",
    "authorized":  "pendiente",
}


class PagoService:

    def __init__(self, session: Session) -> None:
        self._session = session


    def _get_sdk(self):
        if not settings.MP_ACCESS_TOKEN:
            raise RuntimeError("Configure MP_ACCESS_TOKEN")
        try:
            import mercadopago
            return mercadopago.SDK(settings.MP_ACCESS_TOKEN)
        except ImportError:
            raise RuntimeError("pip install mercadopago")


    def _crear_preferencia_mp(self, pedido: Pedido) -> dict:
        sdk = self._get_sdk()
        ngrok_url = settings.NGROK_URL or "http://localhost:8000"

        preference_data = {
            "items": [{
                "title": f"Pedido #{pedido.id} - FoodStore",
                "quantity": 1,
                "unit_price": float(pedido.total),
                "currency_id": "ARS",
            }],
            "external_reference": str(pedido.id),
            "back_urls": {
                "success": f"{ngrok_url}/api/v1/pagos/redirect/{pedido.id}/success",
                "failure": f"{ngrok_url}/api/v1/pagos/redirect/{pedido.id}/failure",
                "pending": f"{ngrok_url}/api/v1/pagos/redirect/{pedido.id}/pending",
            },
            "notification_url": (
                settings.MP_WEBHOOK_URL
                or f"{settings.VITE_API_URL}/api/v1/pagos/webhook"
            ),
            "auto_return": "approved",
        }

        result = sdk.preference().create(preference_data)
        if result.get("status") not in (200, 201):
            raise RuntimeError(f"Error MP: {result.get('response', {}).get('message')}")

        response = result["response"]
        return {
            "preference_id": response["id"],
            "init_point":    response["init_point"],
        }


    def _consultar_pago_mp(self, payment_id: int) -> dict:
        sdk = self._get_sdk()
        result = sdk.payment().get(payment_id)

        if result.get("status") != 200:
            raise RuntimeError(f"Error consultando pago {payment_id}")

        r = result["response"]

        return {
            "mp_payment_id":       r.get("id"),
            "mp_status":           r.get("status"),
            "mp_status_detail":    r.get("status_detail"),
            "mp_merchant_order_id":r.get("merchant_order_id"),
            "payment_method_id":   r.get("payment_method_id"),
            "transaction_amount":  r.get("transaction_amount"),
        }


    def crear_pago(self, pedido_id: int) -> PagoCrearResponse:
        pedido = self._session.get(Pedido, pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

        try:
            mp_data = self._crear_preferencia_mp(pedido)
        except RuntimeError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

        pago = Pago(
            pedido_id=pedido_id,
            mp_status="pendiente",
            mp_preference_id=mp_data["preference_id"],
            external_reference=str(pedido_id),        # lo devuelve MP en el webhook
            idempotency_key=str(uuid.uuid4()),
            transaction_amount=pedido.total,
        )
        self._session.add(pago)
        self._session.commit()
        self._session.refresh(pago)

        return PagoCrearResponse(
            pago_id=pago.id,
            preference_id=mp_data["preference_id"],
            init_point=mp_data["init_point"],
            public_key=settings.MP_PUBLIC_KEY,
        )


    def procesar_webhook(self, data: dict, query_params: Optional[dict] = None) -> dict:
        if not data and query_params:
            data = query_params

        topic    = data.get("type") or data.get("topic")
        data_id  = (data.get("data") or {}).get("id") or data.get("data_id")
        pago_mp_id = data.get("id") or data_id

        if not pago_mp_id:
            return {"status": "ignored", "reason": "No payment ID"}

        if topic not in (None, "payment", "merchant_order"):
            return {"status": "ignored", "reason": f"Topic: {topic}"}

        try:
            mp_info   = self._consultar_pago_mp(int(pago_mp_id))
            estado_mp = mp_info["mp_status"]
            nuevo_estado = ESTADO_MAP.get(estado_mp)

            if not nuevo_estado:
                return {"status": "ignored", "reason": f"Unknown status: {estado_mp}"}

            pago = self._session.exec(select(Pago).where(Pago.mp_payment_id == int(pago_mp_id))).first()

            if not pago:
                ext_ref = str(mp_info.get("mp_merchant_order_id", ""))
                pago = self._session.exec(select(Pago).where(Pago.external_reference == ext_ref)).first()

            if not pago:
                return {"status": "ignored", "reason": "Pago not found"}

            if pago.mp_status not in ("pendiente", "pending"):
                return {"status": "already_processed", "estado": pago.mp_status}

            pago.mp_payment_id      = int(pago_mp_id)
            pago.mp_status          = nuevo_estado
            pago.mp_status_detail   = mp_info.get("mp_status_detail")
            pago.mp_merchant_order_id = mp_info.get("mp_merchant_order_id")
            pago.payment_method_id  = mp_info.get("payment_method_id")
            pago.updated_at         = datetime.now(timezone.utc)
            self._session.add(pago)

            if nuevo_estado == "aprobado":
                pedido = self._session.get(Pedido, pago.pedido_id)

                if pedido:
                    pedido.estado_codigo = "CONFIRMADO"
                    pedido.updated_at    = datetime.now(timezone.utc)
                    self._session.add(pedido)

            return {"status": "processed", "pago_id": pago.id, "estado": nuevo_estado}

        except Exception as e:
            logger.exception("Error procesando webhook")
            return {"status": "error", "reason": str(e)}


    def confirmar_pago(self, pedido_id: int, payment_id: Optional[int] = None) -> PagoEstadoResponse:
        pedido = self._session.get(Pedido, pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

        # Resolver payment_id
        if not payment_id:
            pago_local = self._session.exec(
                select(Pago)
                .where(Pago.pedido_id == pedido_id)
                .order_by(Pago.created_at.desc())
            ).first()
            if pago_local and pago_local.mp_payment_id:
                payment_id = pago_local.mp_payment_id

        if not payment_id:
            # Sin payment_id aún, devolver estado local
            pago_local = self._session.exec(
                select(Pago).where(Pago.pedido_id == pedido_id)
            ).first()
            return PagoEstadoResponse(
                estado=pago_local.mp_status if pago_local else None,
                pedido_id=pedido_id,
            )

        try:
            mp_info = self._consultar_pago_mp(payment_id)
        except RuntimeError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

        nuevo_estado = ESTADO_MAP.get(mp_info["mp_status"], "pendiente")

        pago = self._session.exec(
            select(Pago).where(Pago.mp_payment_id == payment_id)
        ).first()

        if pago:
            pago.mp_status        = nuevo_estado
            pago.mp_status_detail = mp_info.get("mp_status_detail")
            pago.payment_method_id = mp_info.get("payment_method_id")
            pago.updated_at       = datetime.now(timezone.utc)
            self._session.add(pago)

            if nuevo_estado == "aprobado":
                pedido.estado_codigo = "CONFIRMADO"
                pedido.updated_at    = datetime.now(timezone.utc)
                self._session.add(pedido)

            self._session.commit()

        return PagoEstadoResponse(estado=nuevo_estado, pedido_id=pedido_id)