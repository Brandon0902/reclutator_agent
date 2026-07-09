import logging
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from analisis.models import AnalisisDocumento, EstadoAnalisis, EstadoExtraccion, RubricaEvaluacion
from documentos.models import Documento, EstadoDocumento
from .extraccion import extraer_contenido
from .ollama import OllamaClient


logger = logging.getLogger(__name__)


def crear_analisis(documento: Documento, rubrica: RubricaEvaluacion | None = None) -> AnalisisDocumento:
    rubrica = rubrica or RubricaEvaluacion.objects.filter(predeterminada=True, activa=True).first()
    if not rubrica:
        raise ValidationError("No existe una rúbrica predeterminada activa")
    rubrica.validar_pesos()
    with transaction.atomic():
        Documento.objects.select_for_update().get(pk=documento.pk)
        ultimo = AnalisisDocumento.objects.filter(documento=documento, rubrica=rubrica).aggregate(Max("numero"))["numero__max"] or 0
        return AnalisisDocumento.objects.create(
            documento=documento,
            rubrica=rubrica,
            numero=ultimo + 1,
            estado=EstadoAnalisis.PENDIENTE,
            modelo=settings.OLLAMA_MODEL,
        )


def procesar_analisis(analisis_id: int, cliente: OllamaClient | None = None) -> AnalisisDocumento:
    with transaction.atomic():
        analisis = AnalisisDocumento.objects.select_for_update().select_related("documento", "rubrica").get(pk=analisis_id)
        if analisis.estado not in {EstadoAnalisis.PENDIENTE, EstadoAnalisis.ERROR}:
            return analisis
        analisis.estado = EstadoAnalisis.PROCESANDO
        analisis.started_at = timezone.now()
        analisis.error = ""
        analisis.save(update_fields=["estado", "started_at", "error"])
        Documento.objects.filter(pk=analisis.documento_id).update(estado=EstadoDocumento.EN_ANALISIS, error="")

    try:
        contenido = extraer_contenido(analisis.documento)
        if contenido.estado == EstadoExtraccion.SIN_TEXTO:
            analisis.estado = EstadoAnalisis.SIN_TEXTO
            analisis.completed_at = timezone.now()
            analisis.save(update_fields=["estado", "completed_at"])
            return analisis
        if contenido.estado == EstadoExtraccion.ERROR:
            raise RuntimeError(contenido.error or "Falló la extracción de texto")

        criterios_modelo = list(analisis.rubrica.criterios.all())
        analisis.rubrica.validar_pesos()
        criterios = [
            {"id": c.id, "nombre": c.nombre, "descripcion": c.descripcion, "obligatorio": c.obligatorio}
            for c in criterios_modelo
        ]
        resultado = (cliente or OllamaClient()).evaluar(contenido.texto, criterios)
        pesos = {c.id: c.peso for c in criterios_modelo}
        puntuacion = sum(Decimal(str(item["puntuacion"])) * pesos[item["criterio_id"]] / Decimal("100") for item in resultado["criterios"])

        analisis.perfil = resultado["perfil"]
        analisis.resumen = resultado["resumen"]
        analisis.fortalezas = resultado["fortalezas"]
        analisis.brechas = resultado["brechas"]
        analisis.resultados_criterios = resultado["criterios"]
        analisis.puntuacion = puntuacion.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        analisis.estado = EstadoAnalisis.COMPLETADO
        analisis.completed_at = timezone.now()
        analisis.save()
        Documento.objects.filter(pk=analisis.documento_id).update(estado=EstadoDocumento.ANALIZADO, error="")
        logger.info("Análisis completado id=%s documento=%s puntuacion=%s", analisis.pk, analisis.documento_id, analisis.puntuacion)
    except Exception as exc:
        analisis.estado = EstadoAnalisis.ERROR
        analisis.error = str(exc)[:2000]
        analisis.completed_at = timezone.now()
        analisis.save(update_fields=["estado", "error", "completed_at"])
        Documento.objects.filter(pk=analisis.documento_id).update(estado=EstadoDocumento.ERROR_ANALISIS, error=str(exc)[:2000])
        logger.exception("Error analizando documento=%s analisis=%s", analisis.documento_id, analisis.pk)
    return analisis
