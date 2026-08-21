import logging

from django.db import transaction
from django.utils import timezone

from documentos.exceptions import DocumentoInvalidoError
from documentos.models import OrigenDocumento
from documentos.services.documentos import DocumentoRecibido, recibir_documento
from integraciones.models import EstadoEventoWebhook, EstadoMensajeWhatsApp, EventoWebhook, MensajeWhatsApp
from integraciones.services.whatsapp_cloud import WhatsAppCloudClient


logger = logging.getLogger(__name__)


def _actualizar_evento(evento_id: int) -> None:
    mensajes = MensajeWhatsApp.objects.filter(evento_id=evento_id)
    if mensajes.filter(estado__in=[EstadoMensajeWhatsApp.RECIBIDO, EstadoMensajeWhatsApp.PENDIENTE]).exists():
        return
    estado = EstadoEventoWebhook.ERROR if mensajes.filter(estado=EstadoMensajeWhatsApp.ERROR).exists() else EstadoEventoWebhook.PROCESADO
    EventoWebhook.objects.filter(pk=evento_id).update(estado=estado, procesado_at=timezone.now())


def procesar_mensaje_whatsapp(mensaje_id: int, cliente=None) -> MensajeWhatsApp:
    with transaction.atomic():
        mensaje = MensajeWhatsApp.objects.select_for_update().get(pk=mensaje_id)
        if mensaje.estado not in {EstadoMensajeWhatsApp.RECIBIDO, EstadoMensajeWhatsApp.ERROR}:
            return mensaje
        mensaje.estado = EstadoMensajeWhatsApp.PENDIENTE
        mensaje.error = ""
        mensaje.save(update_fields=["estado", "error"])

    try:
        if mensaje.tipo != "document":
            mensaje.estado = EstadoMensajeWhatsApp.IGNORADO
        elif mensaje.mime_type != "application/pdf" or not mensaje.media_id:
            mensaje.estado = EstadoMensajeWhatsApp.IGNORADO
            mensaje.error = "El mensaje no contiene un documento PDF procesable"
        else:
            api = cliente or WhatsAppCloudClient()
            media_url = api.obtener_media_url(mensaje.media_id)
            contenido, mime_descargado = api.descargar_media(media_url)
            mime_efectivo = mime_descargado if mime_descargado == "application/pdf" else mensaje.mime_type
            documento, _duplicado = recibir_documento(DocumentoRecibido(
                origen=OrigenDocumento.WHATSAPP,
                nombre_original=mensaje.nombre_archivo or "curriculum.pdf",
                contenido=contenido,
                mime_type=mime_efectivo,
                id_mensaje_origen=mensaje.wamid,
                remitente=mensaje.nombre_perfil,
                telefono=mensaje.wa_id,
                metadata={"wamid": mensaje.wamid, "media_id": mensaje.media_id},
            ))
            mensaje.documento = documento
            mensaje.estado = EstadoMensajeWhatsApp.PROCESADO
            mensaje.procesado_at = timezone.now()
            mensaje.error = ""
            mensaje.save(update_fields=["documento", "estado", "procesado_at", "error"])
            _actualizar_evento(mensaje.evento_id)
            return mensaje
    except DocumentoInvalidoError as exc:
        mensaje.estado = EstadoMensajeWhatsApp.IGNORADO
        mensaje.error = str(exc)[:2000]
    except Exception as exc:
        logger.exception("Error procesando mensaje WhatsApp id=%s", mensaje_id)
        mensaje.estado = EstadoMensajeWhatsApp.ERROR
        mensaje.error = str(exc)[:2000]

    mensaje.procesado_at = timezone.now()
    mensaje.save(update_fields=["estado", "error", "procesado_at"])
    _actualizar_evento(mensaje.evento_id)
    return mensaje
