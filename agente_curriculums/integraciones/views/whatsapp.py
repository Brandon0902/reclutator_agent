import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from integraciones.whatsapp.services import registrar_evento
from integraciones.whatsapp.signatures import firma_valida


logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    if request.method == "GET":
        token = request.GET.get("hub.verify_token", "")
        if (
            settings.WHATSAPP_VERIFY_TOKEN
            and request.GET.get("hub.mode") == "subscribe"
            and hmac.compare_digest(token, settings.WHATSAPP_VERIFY_TOKEN)
        ):
            return HttpResponse(request.GET.get("hub.challenge", ""))
        return HttpResponse(status=403)

    body = request.body
    if len(body) > settings.WHATSAPP_WEBHOOK_MAX_BODY_KB * 1024:
        logger.warning("Webhook WhatsApp rechazado por tamaño")
        return JsonResponse({"status": "too_large"}, status=413)
    if not firma_valida(body, request.headers.get("X-Hub-Signature-256", "")):
        logger.warning("Firma WhatsApp inválida")
        return HttpResponse(status=403)
    try:
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("El payload no es un objeto")
    except (UnicodeDecodeError, ValueError, TypeError):
        logger.warning("Payload WhatsApp inválido")
        return JsonResponse({"status": "invalid"}, status=400)

    evento, creado, mensajes = registrar_evento(body, payload)
    logger.info(
        "Webhook WhatsApp registrado evento=%s nuevo=%s mensajes=%s estado=%s",
        evento.pk, creado, mensajes, evento.estado,
    )
    return JsonResponse({"status": "accepted", "event_id": evento.pk, "duplicate": not creado})
