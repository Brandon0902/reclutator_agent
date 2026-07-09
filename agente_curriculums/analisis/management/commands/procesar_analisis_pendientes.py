from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from analisis.models import AnalisisDocumento, EstadoAnalisis, RubricaEvaluacion
from analisis.services import crear_analisis, procesar_analisis
from documentos.models import Documento, EstadoDocumento


class Command(BaseCommand):
    help = "Crea y procesa análisis pendientes con la rúbrica predeterminada"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=settings.ANALYSIS_BATCH_SIZE)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1:
            raise CommandError("--limit debe ser mayor que cero")
        rubrica = RubricaEvaluacion.objects.filter(predeterminada=True, activa=True).first()
        if not rubrica:
            raise CommandError("No existe una rúbrica predeterminada activa")
        rubrica.validar_pesos()

        creados = 0
        candidatos = Documento.objects.filter(
            estado__in=[EstadoDocumento.PENDIENTE_ANALISIS, EstadoDocumento.ERROR_ANALISIS]
        ).exclude(analisis__rubrica=rubrica).order_by("fecha_recepcion")[:limit]
        for documento in candidatos:
            crear_analisis(documento, rubrica)
            creados += 1

        ids = list(
            AnalisisDocumento.objects.filter(estado=EstadoAnalisis.PENDIENTE)
            .order_by("created_at").values_list("id", flat=True)[:limit]
        )
        completados = errores = sin_texto = 0
        for analisis_id in ids:
            resultado = procesar_analisis(analisis_id)
            if resultado.estado == EstadoAnalisis.COMPLETADO:
                completados += 1
            elif resultado.estado == EstadoAnalisis.SIN_TEXTO:
                sin_texto += 1
            elif resultado.estado == EstadoAnalisis.ERROR:
                errores += 1
        self.stdout.write(self.style.SUCCESS(
            f"Creados: {creados} | Completados: {completados} | Sin texto: {sin_texto} | Errores: {errores}"
        ))
