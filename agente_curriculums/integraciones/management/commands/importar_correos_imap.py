import imaplib
import logging
import ssl

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from documentos.exceptions import DocumentoInvalidoError
from documentos.models import OrigenDocumento
from documentos.services import DocumentoRecibido, recibir_documento
from integraciones.models import MensajeExternoProcesado
from integraciones.services.imap_client import IMAPClient, MensajeIMAP


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Importa adjuntos PDF no leídos desde un buzón IMAP"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20, help="Máximo de mensajes no leídos a revisar")
        parser.add_argument("--dry-run", action="store_true", help="Comprueba conexión y cuenta mensajes sin procesarlos")

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1:
            raise CommandError("--limit debe ser mayor que cero")

        contador = {"revisados": 0, "guardados": 0, "duplicados": 0, "ignorados": 0, "errores": 0}
        logger.info("Comando importar_correos_imap ejecutado limit=%s dry_run=%s", limit, options["dry_run"])
        try:
            with IMAPClient() as client:
                uids = client.buscar_no_leidos(limit)
                if options["dry_run"]:
                    self.stdout.write(self.style.SUCCESS(
                        f"Conexión IMAP correcta | Carpeta: {client.folder} | No leídos encontrados: {len(uids)}"
                    ))
                    return

                contador["revisados"] = len(uids)
                for uid in uids:
                    clave = client.clave_mensaje(uid)
                    anterior = MensajeExternoProcesado.objects.filter(
                        origen=OrigenDocumento.IMAP,
                        id_mensaje=clave,
                    ).first()
                    if anterior and anterior.estado in {"PROCESADO", "IGNORADO"}:
                        continue
                    self._procesar_mensaje(client, uid, contador)
        except (ImproperlyConfigured, imaplib.IMAP4.error, OSError, ssl.SSLError) as exc:
            logger.error("Error de conexión IMAP: %s", exc.__class__.__name__)
            raise CommandError(f"No fue posible completar la conexión IMAP: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(
            "Revisados: {revisados} | Guardados: {guardados} | Duplicados: {duplicados} | "
            "Ignorados: {ignorados} | Errores: {errores}".format(**contador)
        ))

    def _procesar_mensaje(self, client: IMAPClient, uid: str, contador: dict[str, int]) -> None:
        clave = client.clave_mensaje(uid)
        try:
            mensaje = client.obtener_mensaje(uid)
            metadata = self._metadata(mensaje, client)
            if not mensaje.adjuntos_pdf:
                MensajeExternoProcesado.objects.update_or_create(
                    origen=OrigenDocumento.IMAP,
                    id_mensaje=clave,
                    defaults={"estado": "IGNORADO", "error": "", "metadata": metadata},
                )
                contador["ignorados"] += 1
                logger.info("Mensaje IMAP ignorado sin PDF uid=%s", uid)
                return

            errores_adjuntos: list[str] = []
            for adjunto in mensaje.adjuntos_pdf:
                try:
                    _, duplicado = recibir_documento(DocumentoRecibido(
                        origen=OrigenDocumento.IMAP,
                        nombre_original=adjunto.nombre,
                        contenido=adjunto.contenido,
                        mime_type=adjunto.mime_type,
                        id_mensaje_origen=clave,
                        remitente=mensaje.remitente,
                        correo=mensaje.correo,
                        metadata=metadata,
                    ))
                    contador["duplicados" if duplicado else "guardados"] += 1
                except DocumentoInvalidoError as exc:
                    errores_adjuntos.append(f"{adjunto.nombre}: {exc}")
                    logger.warning("Adjunto IMAP inválido uid=%s nombre=%s", uid, adjunto.nombre)

            if errores_adjuntos:
                raise DocumentoInvalidoError("; ".join(errores_adjuntos))

            MensajeExternoProcesado.objects.update_or_create(
                origen=OrigenDocumento.IMAP,
                id_mensaje=clave,
                defaults={"estado": "PROCESADO", "error": "", "metadata": metadata},
            )
            if settings.IMAP_MARK_AS_READ:
                try:
                    client.marcar_como_leido(uid)
                except (imaplib.IMAP4.error, OSError) as exc:
                    MensajeExternoProcesado.objects.filter(
                        origen=OrigenDocumento.IMAP, id_mensaje=clave
                    ).update(estado="ERROR", error="No se pudo marcar el mensaje como leído")
                    raise exc
            logger.info("Mensaje IMAP procesado uid=%s adjuntos=%s", uid, len(mensaje.adjuntos_pdf))
        except Exception as exc:
            contador["errores"] += 1
            MensajeExternoProcesado.objects.update_or_create(
                origen=OrigenDocumento.IMAP,
                id_mensaje=clave,
                defaults={"estado": "ERROR", "error": str(exc)[:2000], "metadata": {"imap_uid": uid}},
            )
            logger.exception("Error procesando mensaje IMAP uid=%s", uid)

    @staticmethod
    def _metadata(mensaje: MensajeIMAP, client: IMAPClient) -> dict:
        return {
            "subject": mensaje.asunto,
            "received_date": mensaje.fecha,
            "message_id": mensaje.message_id,
            "imap_uid": mensaje.uid,
            "imap_uidvalidity": client.uidvalidity,
            "imap_folder": client.folder,
        }
