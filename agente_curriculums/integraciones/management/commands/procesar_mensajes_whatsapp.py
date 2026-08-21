from django.core.management.base import BaseCommand, CommandError

from integraciones.models import EstadoMensajeWhatsApp, MensajeWhatsApp
from integraciones.whatsapp.processor import procesar_mensaje_whatsapp


class Command(BaseCommand):
    help = "Descarga y procesa documentos pendientes recibidos por WhatsApp"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        limite = options["limit"]
        if limite < 1:
            raise CommandError("--limit debe ser mayor que cero")
        ids = list(MensajeWhatsApp.objects.filter(
            estado__in=[EstadoMensajeWhatsApp.RECIBIDO, EstadoMensajeWhatsApp.ERROR],
        ).order_by("recibido_at").values_list("id", flat=True)[:limite])
        procesados = ignorados = errores = 0
        for mensaje_id in ids:
            mensaje = procesar_mensaje_whatsapp(mensaje_id)
            procesados += mensaje.estado == EstadoMensajeWhatsApp.PROCESADO
            ignorados += mensaje.estado == EstadoMensajeWhatsApp.IGNORADO
            errores += mensaje.estado == EstadoMensajeWhatsApp.ERROR
        self.stdout.write(self.style.SUCCESS(
            f"WhatsApp procesados: {procesados} | Ignorados: {ignorados} | Errores: {errores}"
        ))
