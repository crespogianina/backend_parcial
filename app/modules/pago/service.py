import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import settings
from app.modules.pago.models import Pago
from app.modules.pago.schemas import PagoCrearResponse, PagoEstadoResponse
from app.modules.pago.unit_of_work import PagoUnitOfWork
from app.modules.pedido.models import Pedido
from app.modules.pedido.service import PedidoService

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

    # revisado
    def __init__(self, session: Session) -> None:
        self._session = session
        self._session_pedido = PedidoService(session)
        
    # ── Helpers privados ──────────────────────────────────────────────────────

    # revisado
    def _get_mp_access_token(self) -> Optional[str]:
        return settings.MP_ACCESS_TOKEN


    # revisado
    def _get_mp_public_key(self) -> Optional[str]:
        return settings.MP_PUBLIC_KEY
    

    def _obtener_pedido_or_404(self, pedido_id: int) -> Pedido :
        pedido = self._session.get(Pedido, pedido_id)

        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )
        return pedido


    def _crear_preferencia_mp(self, monto: float, titulo: str, pedido_id: int, back_urls: dict) -> dict:
        access_token = self._get_mp_access_token()

        if not access_token:
            raise RuntimeError("MercadoPago no está configurado. Configure MP_ACCESS_TOKEN")

        try:
            import mercadopago
            sdk = mercadopago.SDK(access_token)

            preference_data = {
                "items": [{
                    "title": titulo,
                    "quantity": 1,
                    # En este caso la orden es un solo ítem genérico.
                    # Podríamos enviar los ítems reales del pedido si quisieramos
                    # mostrar el detalle en el checkout de MP.
                    "unit_price": float(monto),
                    "currency_id": "ARS",  # Moneda: pesos argentinos
                }],
                "external_reference": str(pedido_id),
                "back_urls": back_urls,
                "notification_url": (
                    settings.MP_WEBHOOK_URL
                    or f"{settings.VITE_API_URL}/api/v1/pagos/webhook"
                ),
                "auto_return": "approved",
            }

            result = sdk.preference().create(preference_data)

            if result.get("status") not in (200, 201):
                logger.error("Error creando preferencia MP: %s", result)

                raise RuntimeError(
                    "Error al crear preferencia: "
                    f"{result.get('response', {}).get('message', 'desconocido')}"
                )

            response = result.get("response", {})
            return {
                "preference_id": response.get("id"),
                "init_point": response.get("init_point"),
            }

        except ImportError:
            raise RuntimeError("pip install mercadopago")
        except Exception as e:
            logger.exception("Error inesperado al crear preferencia MP")
            raise RuntimeError(f"Error de conexión con MP: {str(e)}")


    def _consultar_pago_mp(self, payment_id: int) -> dict:
        access_token = self._get_mp_access_token()
        
        if not access_token:
            raise RuntimeError("MP no configurado")

        try:
            import mercadopago
            sdk = mercadopago.SDK(access_token)
            result = sdk.payment().get(payment_id)

            if result.get("status") != 200:
                logger.error("Error consultando pago MP %s: %s", payment_id, result)
                raise RuntimeError(f"Error al consultar pago {payment_id}")

            response = result.get("response", {})
            return {
                "mp_payment_id": response.get("id"),
                "mp_status": response.get("status"),
                "mp_status_detail": response.get("status_detail"),
                "mp_merchant_order_id": response.get("merchant_order_id"),
            }

        except ImportError:
            raise RuntimeError("pip install mercadopago")
        except Exception as e:
            logger.exception("Error consultando pago MP %s", payment_id)
            raise RuntimeError(f"Error de conexión con MP: {str(e)}")

    # ─────────────────────────────────────────────────────────

    def crear_pago(self, pedido_id: int) -> PagoCrearResponse:
        pedido = self._obtener_pedido_or_404(pedido_id)

        if not self._get_mp_access_token():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MercadoPago no configurado. Configure MP_ACCESS_TOKEN",
            )

        ngrok_url = settings.NGROK_URL or "http://localhost:8000"
        back_urls = {
            "success": f"{ngrok_url}/api/v1/pagos/redirect/{pedido_id}/success",
            "failure": f"{ngrok_url}/api/v1/pagos/redirect/{pedido_id}/failure",
            "pending": f"{ngrok_url}/api/v1/pagos/redirect/{pedido_id}/pending",
        }

        try:
            mp_data = self._crear_preferencia_mp(
                monto=pedido.total,
                titulo=f"Pedido #{pedido_id} - FoodStore",
                pedido_id=pedido_id,
                back_urls=back_urls,
            )
        except RuntimeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        with PagoUnitOfWork(self._session) as uow:
            pago = Pago(
                pedido_id=pedido_id,
                monto=pedido.total,
                estado="pendiente",           
                mp_preference_id=mp_data["preference_id"],
                mp_init_point=mp_data.get("init_point"),
                idempotency_key=str(uuid.uuid4()),
            )
            uow.pagos.add(pago)

            return PagoCrearResponse(
                pago_id=pago.id,                     # ID de nuestro pago local
                preference_id=mp_data["preference_id"],  # ID de la preferencia en MP
                init_point=mp_data.get("init_point"),     # URL del checkout de MP
                public_key=self._get_mp_public_key(),     # Public Key para el SDK frontend
            )


    def procesar_webhook(self, data: dict, query_params: Optional[dict] = None) -> dict:
        logger.info("Webhook recibido: data=%s qs=%s", data, query_params or {})

        if not data and query_params:
            data = query_params

        topic = data.get("type") or data.get("topic")
        data_id = data.get("data_id") or (data.get("data") or {}).get("id")
        payment_id = data.get("id")

        if not data_id and query_params:
            data_id = query_params.get("data.id") or query_params.get("id")

        if not topic and query_params:
            topic = query_params.get("topic") or query_params.get("type")

        pago_mp_id = payment_id or data_id

        if not pago_mp_id:
            return {"status": "ignored", "reason": "No payment ID"}

        if topic not in (None, "payment", "merchant_order"):
            return {"status": "ignored", "reason": f"Topic: {topic}"}

        try:
            mp_info = self._consultar_pago_mp(int(pago_mp_id))
            estado_mp = mp_info.get("mp_status")

            if estado_mp == "approved":
                nuevo_estado = "aprobado"

            elif estado_mp in ("rejected", "cancelled", "refunded", "charged_back"):
                nuevo_estado = "rechazado"

            elif estado_mp in ("pending", "in_process", "authorized"):
                nuevo_estado = "pendiente"

            else:
                return {"status": "ignored", "reason": f"Unknown status: {estado_mp}"}

            with PagoUnitOfWork(self._session) as uow:
                pago = uow.pagos.get_by_mp_payment_id(int(pago_mp_id))

                if not pago and mp_info.get("mp_merchant_order_id"):
                    pago = uow.pagos.get_by_mp_merchant_order_id(
                        mp_info["mp_merchant_order_id"]
                    )

                if not pago:
                    return {"status": "ignored", "reason": "Pago not found in local DB"}

                if pago.estado != "pendiente":
                    return {"status": "already_processed", "estado": pago.estado}

                pago.mp_payment_id = int(pago_mp_id)
                pago.mp_status = estado_mp
                pago.mp_status_detail = mp_info.get("mp_status_detail")
                pago.mp_merchant_order_id = mp_info.get("mp_merchant_order_id")
                pago.estado = nuevo_estado
                pago.updated_at = datetime.utcnow()
                uow.pagos.update(pago)

                if nuevo_estado == "aprobado":
                    pedido = self._session.get(Pedido, pago.pedido_id)
                    if pedido:
                        pedido.estado = "pagado"
                        pedido.updated_at = datetime.utcnow()
                        self._session.add(pedido)

                # No se deberia marcar como rechazado?
                if nuevo_estado == "rechazado":
                    pedido = self._session.get(Pedido, pago.pedido_id)

                    if pedido:
                        pedido.estado = "rechazado"
                        pedido.updated_at = datetime.utcnow()
                        self._session.add(pedido)

            return {
                "status": "processed",
                "pago_id": pago.id,
                "estado": nuevo_estado,
                "pedido_id": pago.pedido_id,
            }

        except Exception as e:
            logger.exception("Error procesando webhook MP")
            return {"status": "error", "reason": str(e)}



    def confirmar_pago(self, pedido_id: int, payment_id: Optional[int] = None) -> PagoEstadoResponse:
        pedido = self._obtener_pedido_or_404(pedido_id)

        resolved_payment_id = payment_id

        if not resolved_payment_id:
            with PagoUnitOfWork(self._session) as uow:
                pago_local = uow.pagos.get_ultimo_by_pedido(pedido_id)

                if pago_local and pago_local.mp_payment_id:
                    resolved_payment_id = pago_local.mp_payment_id

        if resolved_payment_id:
            try:
                mp_info = self._consultar_pago_mp(resolved_payment_id)
            except RuntimeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

            estado_mp = mp_info.get("mp_status")

            if estado_mp == "approved":
                nuevo_estado = "aprobado"

            elif estado_mp in ("rejected", "cancelled", "refunded", "charged_back"):
                nuevo_estado = "rechazado"

            else:
                nuevo_estado = "pendiente"

            with PagoUnitOfWork(self._session) as uow:
                pago = uow.pagos.get_by_mp_payment_id(resolved_payment_id)

                if not pago:
                    pago = uow.pagos.get_ultimo_by_pedido(pedido_id)

                if pago:
                    pago.mp_payment_id = resolved_payment_id
                    pago.mp_status = estado_mp
                    pago.mp_status_detail = mp_info.get("mp_status_detail")
                    pago.mp_merchant_order_id = mp_info.get("mp_merchant_order_id")
                    pago.estado = nuevo_estado
                    pago.updated_at = datetime.utcnow()
                    uow.pagos.update(pago)

                    if nuevo_estado == "aprobado":
                        pedido.estado = "pagado"
                        pedido.updated_at = datetime.utcnow()
                        self._session.add(pedido)

                    # No se deberia marcar como rechazado?
                    if nuevo_estado == "rechazado":
                        pedido.estado = "rechazado"
                        pedido.updated_at = datetime.utcnow()
                        self._session.add(pedido)

            return PagoEstadoResponse(estado=nuevo_estado, pedido_id=pedido_id)

        with PagoUnitOfWork(self._session) as uow:
            pago_local = uow.pagos.get_ultimo_by_pedido(pedido_id)

            return PagoEstadoResponse(
                estado=pago_local.estado if pago_local else None,
                pedido_id=pedido_id,
            )