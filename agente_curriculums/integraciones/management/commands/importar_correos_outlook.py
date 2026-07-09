import logging
from django.core.management.base import BaseCommand
from documentos.models import OrigenDocumento
from documentos.services import DocumentoRecibido, recibir_documento
from integraciones.models import MensajeExternoProcesado
from integraciones.services.microsoft_graph import MicrosoftGraphClient
logger = logging.getLogger(__name__)
class Command(BaseCommand):
    help = "Importa adjuntos PDF nuevos desde Microsoft 365"
    def handle(self, *args, **options):
        saved = duplicates = errors = 0; client = MicrosoftGraphClient(); logger.info("Comando importar_correos_outlook ejecutado")
        for msg in client.obtener_mensajes_con_adjuntos():
            mid = msg.get("id", "")
            if not mid or MensajeExternoProcesado.objects.filter(origen=OrigenDocumento.OUTLOOK, id_mensaje=mid).exists(): continue
            try:
                for att in client.obtener_adjuntos(mid):
                    name, mime = att.get("name", ""), att.get("contentType", "")
                    if not name.lower().endswith(".pdf") or mime != "application/pdf": continue
                    _, duplicate = recibir_documento(DocumentoRecibido(origen=OrigenDocumento.OUTLOOK, nombre_original=name, contenido=client.descargar_adjunto(mid, att["id"]), mime_type=mime, id_mensaje_origen=mid, correo=((msg.get("from") or {}).get("emailAddress") or {}).get("address"), remitente=((msg.get("from") or {}).get("emailAddress") or {}).get("name"), metadata={"subject": msg.get("subject", "")}))
                    duplicates += int(duplicate); saved += int(not duplicate)
                MensajeExternoProcesado.objects.create(origen=OrigenDocumento.OUTLOOK, id_mensaje=mid)
            except Exception as exc:
                errors += 1; logger.exception("Error procesando mensaje Outlook id=%s", mid)
                MensajeExternoProcesado.objects.update_or_create(origen=OrigenDocumento.OUTLOOK, id_mensaje=mid, defaults={"estado": "ERROR", "error": str(exc)[:2000]})
        self.stdout.write(f"Guardados: {saved} | Duplicados: {duplicates} | Errores: {errors}")
