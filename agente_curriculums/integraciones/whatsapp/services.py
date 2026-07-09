import hashlib

from django.db import transaction
from django.utils import timezone

from integraciones.models import EstadoEventoWebhook, EventoWebhook, MensajeWhatsApp
from .parsers import extraer_mensajes, resumen_sanitizado


@transaction.atomic
def registrar_evento(body: bytes, payload: dict) -> tuple[EventoWebhook, bool, int]:
    digest = hashlib.sha256(body).hexdigest()
    evento, creado = EventoWebhook.objects.get_or_create(
        payload_sha256=digest,
        defaults={"proveedor": "WHATSAPP", "objeto": str(payload.get("object", ""))[:80]},
    )
    if not creado:
        return evento, False, 0

    mensajes = extraer_mensajes(payload)
    nuevos = 0
    for datos_originales in mensajes:
        datos = datos_originales.copy()
        wamid = datos.pop("wamid")
        _, mensaje_creado = MensajeWhatsApp.objects.get_or_create(
            wamid=wamid, defaults={"evento": evento, **datos}
        )
        nuevos += int(mensaje_creado)

    evento.payload_sanitizado = resumen_sanitizado(payload, mensajes)
    if mensajes:
        evento.estado = EstadoEventoWebhook.RECIBIDO
    else:
        evento.estado = EstadoEventoWebhook.IGNORADO
        evento.procesado_at = timezone.now()
    evento.save(update_fields=["payload_sanitizado", "estado", "procesado_at"])
    return evento, True, nuevos
