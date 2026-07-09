from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from analisis.models import EstadoAnalisis
from vacantes.models import EstadoEvaluacion, EvaluacionVacante
from vacantes.services import procesar_evaluacion_vacante


class Command(BaseCommand):
    help = "Procesa evaluaciones de vacantes pendientes"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=2)
        parser.add_argument("--recover-stale-minutes", type=int, default=30)

    def handle(self, *args, **options):
        recuperadas = self._recuperar_colgadas(options["recover_stale_minutes"])
        ids = list(EvaluacionVacante.objects.filter(estado=EstadoEvaluacion.PENDIENTE).order_by("created_at", "id").values_list("id", flat=True)[:options["limit"]])
        completadas = errores = sin_texto = 0
        for evaluacion_id in ids:
            resultado = procesar_evaluacion_vacante(evaluacion_id)
            completadas += resultado.estado == EstadoEvaluacion.COMPLETADA
            errores += resultado.estado == EstadoEvaluacion.ERROR
            sin_texto += resultado.estado == EstadoEvaluacion.SIN_TEXTO
        self.stdout.write(self.style.SUCCESS(f"Evaluaciones completadas: {completadas} | Sin texto: {sin_texto} | Errores: {errores} | Recuperadas: {recuperadas}"))

    def _recuperar_colgadas(self, minutos):
        if minutos < 0:
            return 0
        limite = timezone.now() - timedelta(minutes=minutos)
        evaluaciones = list(
            EvaluacionVacante.objects.filter(estado=EstadoEvaluacion.PROCESANDO, started_at__lte=limite)
            .select_related("analisis")
        )
        for evaluacion in evaluaciones:
            if evaluacion.analisis_id:
                evaluacion.analisis.estado = EstadoAnalisis.ERROR
                evaluacion.analisis.error = "Evaluacion recuperada por worker despues de quedar en PROCESANDO"
                evaluacion.analisis.completed_at = timezone.now()
                evaluacion.analisis.save(update_fields=["estado", "error", "completed_at"])
            evaluacion.estado = EstadoEvaluacion.PENDIENTE
            evaluacion.error = ""
            evaluacion.analisis = None
            evaluacion.started_at = None
            evaluacion.completed_at = None
            evaluacion.save(update_fields=["estado", "error", "analisis", "started_at", "completed_at"])
        return len(evaluaciones)
