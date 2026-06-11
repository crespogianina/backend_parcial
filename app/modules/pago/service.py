import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import settings
from app.modules.pago.models import Pago
from app.modules.pago.schemas import PagoCrearResponse, PagoEstadoResponse
from app.modules.pago.unit_of_work import PagoUnitOfWork
from app.modules.pedido.models import Pedido
from app.modules.pedido.service import PedidoService
from app.modules.usuarios.schemas import UserPublic

logger = logging.getLogger(__name__)

# ESTADO_MAP = {
#     "approved":    "aprobado",
#     "rejected":    "rechazado",
#     "cancelled":   "rechazado",
#     "refunded":    "rechazado",
#     "charged_back":"rechazado",
#     "pending":     "pendiente",
#     "in_process":  "pendiente",
#     "authorized":  "pendiente",
# }

ESTADOS_MP_TERMINALES = {"approved", "rejected", "cancelled", "refunded", "charged_back"}
ESTADOS_MP_PENDIENTES = {"pending", "in_process", "authorized"}
ESTADOS_MP_RECHAZADOS = {"rejected", "cancelled", "refunded", "charged_back"}
ESTADO_INICIAL = "creado" 

class WebhookTransientError(Exception):
    """[H] Error transitorio (MP no responde, DB caída). El router debe
    devolver non-200: el ERD documenta que MP reintenta si no recibe 200."""

class PagoService:

    def __init__(self, session: Session) -> None:
        self._session = session
        self._pedido_service = PedidoService(session)
        
    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_mp_access_token(self) -> Optional[str]:
        return settings.MP_ACCESS_TOKEN


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


    def _crear_preferencia_mp(self, monto: float, titulo: str, external_reference: str, idempotency_key: str, back_urls: dict) -> dict:
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
                    "unit_price": float(monto),
                    "currency_id": "ARS",
                }],
                "external_reference": external_reference,
                "back_urls": back_urls,
                "notification_url": (
                    settings.MP_WEBHOOK_URL
                    or f"{settings.VITE_API_URL}/api/v1/pagos/webhook"
                ),
                "auto_return": "approved",
            }

            request_options = mercadopago.config.RequestOptions()
            request_options.custom_headers = {"x-idempotency-key": idempotency_key}

            result = sdk.preference().create(preference_data, request_options)

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

        except RuntimeError:
            raise
        
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
                "payment_method_id":  response.get("payment_method_id"),
                "external_reference": response.get("external_reference"),
            }

        except ImportError:
            raise RuntimeError("pip install mercadopago")
        
        except RuntimeError:
            raise

        except Exception as e:
            logger.exception("Error consultando pago MP %s", payment_id)
            raise RuntimeError(f"Error de conexión con MP: {str(e)}")


    def _aplicar_estado_mp(self, pago: Pago, mp_info: dict) -> str:
        pago.mp_payment_id = mp_info.get("mp_payment_id") or pago.mp_payment_id
        pago.mp_status = mp_info["mp_status"]            
        pago.mp_status_detail = mp_info.get("mp_status_detail")
        pago.payment_method_id = mp_info.get("payment_method_id")
        pago.updated_at = datetime.now(timezone.utc)

        return pago.mp_status
    
    # ─────────────────────────────────────────────────────────

    def crear_pago(self, pedido_id: int, usuario: UserPublic) -> PagoCrearResponse:
        pedido = self._obtener_pedido_or_404(pedido_id)

        if pedido.usuario_id != usuario.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo podés pagar tus propios pedidos.",
            )
        
        if pedido.forma_pago_codigo != "MERCADOPAGO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El pedido tiene forma de pago '{pedido.forma_pago_codigo}', "
                       f"no corresponde checkout de MercadoPago.",
            )
        
        if pedido.estado_codigo != "PENDIENTE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El pedido está {pedido.estado_codigo}, no admite pago.",
            )
        
        if not self._get_mp_access_token():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MercadoPago no configurado. Configure MP_ACCESS_TOKEN",
            )
        

        with PagoUnitOfWork(self._session) as uow:
            pendiente = uow.pagos.get_pendiente_by_pedido(pedido_id)
 
        if pendiente and pendiente.mp_preference_id:
            return PagoCrearResponse(
                pago_id=pendiente.id,
                preference_id=pendiente.mp_preference_id,
                init_point=pendiente.mp_init_point,
                public_key=self._get_mp_public_key(),
            )
 
        ngrok_url = settings.NGROK_URL or "http://localhost:8000"
        back_urls = {
            "success": f"{ngrok_url}/api/v1/pagos/redirect/{pedido_id}/success",
            "failure": f"{ngrok_url}/api/v1/pagos/redirect/{pedido_id}/failure",
            "pending": f"{ngrok_url}/api/v1/pagos/redirect/{pedido_id}/pending",
        }

        external_reference = f"{pedido_id}-{uuid.uuid4().hex[:8]}"
        idempotency_key = str(uuid.uuid4())

        try:
            mp_data = self._crear_preferencia_mp(
                monto=pedido.total,
                titulo=f"Pedido #{pedido_id} - FoodStore",
                external_reference=external_reference,
                idempotency_key=idempotency_key,        
                back_urls=back_urls,
            )

        except RuntimeError as e:
            raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        with PagoUnitOfWork(self._session) as uow:
            pago = Pago(
                pedido_id=pedido_id,
                transaction_amount=pedido.total,
                mp_status=ESTADO_INICIAL,
                external_reference=external_reference,
                idempotency_key=idempotency_key,
                mp_preference_id=mp_data["preference_id"],
                mp_init_point=mp_data.get("init_point"),
            )
            uow.pagos.add(pago)

            return PagoCrearResponse(
                pago_id=pago.id,                     
                preference_id=mp_data["preference_id"],  
                init_point=mp_data.get("init_point"),     
                public_key=self._get_mp_public_key(),    
            )


    async def procesar_webhook(self, data: dict, query_params: Optional[dict] = None) -> dict:
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

        if topic not in (None, "payment"):
            return {"status": "ignored", "reason": f"Topic: {topic}"}
 
        try:
            mp_info = self._consultar_pago_mp(int(pago_mp_id))
            estado_mp = mp_info.get("mp_status")

            if estado_mp not in ESTADOS_MP_TERMINALES | ESTADOS_MP_PENDIENTES:
                return {"status": "ignored", "reason": f"Unknown status: {estado_mp}"}

            with PagoUnitOfWork(self._session) as uow:
                pago = uow.pagos.get_by_mp_payment_id(int(pago_mp_id))

                if not pago and mp_info.get("external_reference"):
                    pago = uow.pagos.get_by_external_reference(
                        mp_info["external_reference"]
                    )

                if not pago:
                    return {"status": "ignored", "reason": "Pago not found in local DB"}

                if pago.mp_status in ESTADOS_MP_TERMINALES:
                    return {"status": "already_processed", "estado": pago.mp_status}

                self._aplicar_estado_mp(pago, mp_info)
                uow.pagos.update(pago)
                pedido_id = pago.pedido_id
                pago_id = pago.id

            if estado_mp == "approved":
                await self._pedido_service.confirmar_por_pago(pedido_id)
 
            return {
                "status": "processed",
                "pago_id": pago_id,
                "estado": estado_mp,
                "pedido_id": pedido_id,
            }

        except WebhookTransientError:
            raise

        except Exception as e:
            logger.exception("Error procesando webhook MP")
            return {"status": "error", "reason": str(e)}



    async def confirmar_pago( self, pedido_id: int, payment_id: Optional[int] = None, usuario: Optional[UserPublic] = None ) -> PagoEstadoResponse:
        pedido = self._obtener_pedido_or_404(pedido_id)

        if usuario is not None:
            es_admin = "ADMIN" in {r.upper() for r in usuario.roles}

            if not es_admin and pedido.usuario_id != usuario.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tenés permiso para consultar este pago.",
                )
 
        resolved_payment_id = payment_id
 
        if not resolved_payment_id:
            with PagoUnitOfWork(self._session) as uow:
                pago_local = uow.pagos.get_ultimo_by_pedido(pedido_id)

                if pago_local and pago_local.mp_payment_id:
                    resolved_payment_id = pago_local.mp_payment_id
 
        if not resolved_payment_id:
            with PagoUnitOfWork(self._session) as uow:
                pago_local = uow.pagos.get_ultimo_by_pedido(pedido_id)

                return PagoEstadoResponse(
                    estado=pago_local.mp_status if pago_local else None, 
                    pedido_id=pedido_id,
                )
 
        try:
            mp_info = self._consultar_pago_mp(resolved_payment_id)

        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
 
        estado_mp = mp_info.get("mp_status")
 
        with PagoUnitOfWork(self._session) as uow:
            pago = uow.pagos.get_by_mp_payment_id(resolved_payment_id)
 
            if not pago:
                pago = uow.pagos.get_ultimo_by_pedido(pedido_id)
 
            if pago and pago.mp_status not in ESTADOS_MP_TERMINALES:
                self._aplicar_estado_mp(pago, mp_info)
                uow.pagos.update(pago)

            elif pago:
                estado_mp = pago.mp_status   
 
        if estado_mp == "approved":
            await self._pedido_service.confirmar_por_pago(pedido_id)

        if estado_mp in ESTADOS_MP_RECHAZADOS:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Pago no acreditado ({estado_mp}). Podés reintentar el pago.",
            )  
 
        return PagoEstadoResponse(estado=estado_mp, pedido_id=pedido_id)