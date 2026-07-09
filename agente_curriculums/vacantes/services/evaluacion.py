from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

from analisis.models import EstadoAnalisis
from analisis.services import crear_analisis, procesar_analisis
from documentos.models import Documento, EstadoDocumento
from vacantes.models import (
    EjecucionVacante, EstadoEjecucion, EstadoEvaluacion, EstadoVacante, EvaluacionVacante, MensajeVacante, RolMensaje, Vacante,
)


@transaction.atomic
def crear_ejecucion(vacante: Vacante) -> EjecucionVacante:
    vacante = Vacante.objects.select_for_update().select_related("rubrica").get(pk=vacante.pk)
    if vacante.estado not in {EstadoVacante.CONFIRMADA, EstadoVacante.COMPLETADA, EstadoVacante.ERROR} or not vacante.rubrica_id:
        raise ValueError("La vacante debe estar confirmada antes de evaluar")
    activa = vacante.ejecuciones.filter(estado__in=[EstadoEjecucion.PENDIENTE, EstadoEjecucion.PROCESANDO]).exists()
    if activa:
        raise ValueError("La vacante ya tiene una ejecución activa")
    numero = (vacante.ejecuciones.aggregate(Max("numero"))["numero__max"] or 0) + 1
    documentos = list(Documento.objects.all().order_by("id"))
    ejecucion = EjecucionVacante.objects.create(vacante=vacante, numero=numero, total=len(documentos))
    EvaluacionVacante.objects.bulk_create([
        EvaluacionVacante(
            ejecucion=ejecucion, documento=documento,
            estado=EstadoEvaluacion.SIN_TEXTO if documento.estado == EstadoDocumento.SIN_TEXTO else EstadoEvaluacion.PENDIENTE,
            completed_at=timezone.now() if documento.estado == EstadoDocumento.SIN_TEXTO else None,
        ) for documento in documentos
    ])
    vacante.estado = EstadoVacante.EVALUANDO
    vacante.save(update_fields=["estado", "updated_at"])
    _actualizar_ejecucion(ejecucion.id)
    return EjecucionVacante.objects.get(pk=ejecucion.pk)


def _actualizar_ejecucion(ejecucion_id: int) -> EjecucionVacante:
    with transaction.atomic():
        ejecucion = EjecucionVacante.objects.select_for_update().select_related("vacante").get(pk=ejecucion_id)
        conteos = ejecucion.evaluaciones.aggregate(
            completados=Count("id", filter=Q(estado=EstadoEvaluacion.COMPLETADA)),
            sin_texto=Count("id", filter=Q(estado=EstadoEvaluacion.SIN_TEXTO)),
            errores=Count("id", filter=Q(estado=EstadoEvaluacion.ERROR)),
            pendientes=Count("id", filter=Q(estado__in=[EstadoEvaluacion.PENDIENTE, EstadoEvaluacion.PROCESANDO])),
        )
        ejecucion.completados = conteos["completados"]
        ejecucion.sin_texto = conteos["sin_texto"]
        ejecucion.errores = conteos["errores"]
        if conteos["pendientes"]:
            ejecucion.estado = EstadoEjecucion.PROCESANDO if ejecucion.started_at else EstadoEjecucion.PENDIENTE
        else:
            ejecucion.completed_at = timezone.now()
            if ejecucion.errores == ejecucion.total and ejecucion.total:
                ejecucion.estado = EstadoEjecucion.ERROR
            elif ejecucion.errores:
                ejecucion.estado = EstadoEjecucion.PARCIAL
            else:
                ejecucion.estado = EstadoEjecucion.COMPLETADA
        ejecucion.save()
        if ejecucion.estado in {EstadoEjecucion.COMPLETADA, EstadoEjecucion.PARCIAL}:
            Vacante.objects.filter(pk=ejecucion.vacante_id).update(estado=EstadoVacante.COMPLETADA)
            _crear_resumen_final(ejecucion)
        elif ejecucion.estado == EstadoEjecucion.ERROR:
            Vacante.objects.filter(pk=ejecucion.vacante_id).update(estado=EstadoVacante.ERROR)
        return ejecucion


def _crear_resumen_final(ejecucion):
    marcador = {"tipo": "RESULTADO_EJECUCION", "ejecucion_id": ejecucion.id}
    existente = MensajeVacante.objects.filter(
        vacante_id=ejecucion.vacante_id, datos__tipo=marcador["tipo"], datos__ejecucion_id=ejecucion.id
    ).first()
    mejores = list(
        ejecucion.evaluaciones.filter(estado=EstadoEvaluacion.COMPLETADA)
        .select_related("documento", "analisis").order_by("-analisis__puntuacion", "documento_id")[:3]
    )
    if mejores:
        lineas = [f"{item.analisis.perfil.get('nombre') or item.documento.remitente or item.documento.nombre_original}: {item.analisis.puntuacion}" for item in mejores]
        contenido = "Mejores coincidencias de esta ejecución: " + "; ".join(lineas) + ". La clasificación apoya la revisión humana y no constituye una decisión de contratación."
    else:
        contenido = "La ejecución terminó sin candidatos evaluables. Revisa los documentos sin texto o con error."
    if existente:
        existente.contenido = contenido
        existente.datos = marcador
        existente.save(update_fields=["contenido", "datos"])
    else:
        MensajeVacante.objects.create(vacante_id=ejecucion.vacante_id, rol=RolMensaje.AGENTE, contenido=contenido, datos=marcador)


def procesar_evaluacion_vacante(evaluacion_id: int, cliente=None) -> EvaluacionVacante:
    try:
        with transaction.atomic():
            evaluacion = EvaluacionVacante.objects.select_for_update().select_related("ejecucion__vacante__rubrica", "documento").get(pk=evaluacion_id)
            if evaluacion.estado != EstadoEvaluacion.PENDIENTE:
                return evaluacion
            evaluacion.estado = EstadoEvaluacion.PROCESANDO
            evaluacion.started_at = timezone.now()
            evaluacion.error = ""
            evaluacion.save(update_fields=["estado", "started_at", "error"])
            EjecucionVacante.objects.filter(pk=evaluacion.ejecucion_id, started_at__isnull=True).update(started_at=timezone.now(), estado=EstadoEjecucion.PROCESANDO)
            analisis = crear_analisis(evaluacion.documento, evaluacion.ejecucion.vacante.rubrica)
            evaluacion.analisis = analisis
            evaluacion.save(update_fields=["analisis"])
    except Exception as exc:
        evaluacion = EvaluacionVacante.objects.get(pk=evaluacion_id)
        evaluacion.estado = EstadoEvaluacion.ERROR
        evaluacion.error = str(exc)[:2000]
        evaluacion.completed_at = timezone.now()
        evaluacion.save(update_fields=["estado", "error", "completed_at"])
        _actualizar_ejecucion(evaluacion.ejecucion_id)
        return evaluacion
    resultado = procesar_analisis(analisis.id, cliente)
    evaluacion.refresh_from_db()
    if resultado.estado == EstadoAnalisis.COMPLETADO:
        evaluacion.estado = EstadoEvaluacion.COMPLETADA
    elif resultado.estado == EstadoAnalisis.SIN_TEXTO:
        evaluacion.estado = EstadoEvaluacion.SIN_TEXTO
    else:
        evaluacion.estado = EstadoEvaluacion.ERROR
        evaluacion.error = resultado.error
    evaluacion.completed_at = timezone.now()
    evaluacion.save(update_fields=["estado", "error", "completed_at"])
    _actualizar_ejecucion(evaluacion.ejecucion_id)
    return evaluacion


@transaction.atomic
def reintentar_errores(ejecucion: EjecucionVacante) -> EjecucionVacante:
    ejecucion = EjecucionVacante.objects.select_for_update().select_related("vacante").get(pk=ejecucion.pk)
    if ejecucion.estado not in {EstadoEjecucion.PARCIAL, EstadoEjecucion.ERROR}:
        raise ValueError("La ejecución no tiene errores disponibles para reintentar")
    actualizadas = ejecucion.evaluaciones.filter(estado=EstadoEvaluacion.ERROR).update(
        estado=EstadoEvaluacion.PENDIENTE, error="", started_at=None, completed_at=None
    )
    if not actualizadas:
        raise ValueError("La ejecución no tiene evaluaciones con error")
    ejecucion.estado = EstadoEjecucion.PENDIENTE
    ejecucion.errores = 0
    ejecucion.error = ""
    ejecucion.completed_at = None
    ejecucion.save(update_fields=["estado", "errores", "error", "completed_at"])
    Vacante.objects.filter(pk=ejecucion.vacante_id).update(estado=EstadoVacante.EVALUANDO)
    return ejecucion
