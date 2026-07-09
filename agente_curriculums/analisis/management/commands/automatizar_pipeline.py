import logging
import time
from time import monotonic

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ejecuta periodicamente importacion IMAP, analisis local y tareas conversacionales"

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=settings.ANALYSIS_INTERVAL_SECONDS)
        parser.add_argument("--conversation-interval", type=int, default=10)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        intervalo_pesado = options["interval"]
        intervalo_conversacion = max(1, options["conversation_interval"])
        siguiente_ciclo_pesado = monotonic()

        while True:
            try:
                call_command("procesar_conversaciones", limit=2)
            except Exception:
                logger.exception("Fallo el ciclo de conversaciones")

            try:
                call_command("procesar_evaluaciones_vacantes", limit=2)
            except Exception:
                logger.exception("Fallo el ciclo de evaluaciones por vacante")

            if monotonic() >= siguiente_ciclo_pesado:
                try:
                    call_command("importar_correos_imap", limit=20)
                except Exception:
                    logger.exception("Fallo el ciclo de importacion IMAP")
                try:
                    call_command("procesar_analisis_pendientes", limit=settings.ANALYSIS_BATCH_SIZE)
                except Exception:
                    logger.exception("Fallo el ciclo de analisis")
                siguiente_ciclo_pesado = monotonic() + intervalo_pesado

            if options["once"]:
                return
            time.sleep(intervalo_conversacion)
