from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework.test import APIClient

from analisis.models import AnalisisDocumento, CriterioEvaluacion, EstadoAnalisis, RubricaEvaluacion
from documentos.models import Documento, EstadoDocumento, OrigenDocumento
from vacantes.models import EjecucionVacante, EstadoEjecucion, EstadoEvaluacion, EstadoVacante, EvaluacionVacante, RolMensaje, Vacante
from vacantes.services.evaluacion import _actualizar_ejecucion


pytestmark = pytest.mark.django_db


def escenario_ranking(cantidad=12):
    usuario = get_user_model().objects.create_user("ranking")
    rubrica = RubricaEvaluacion.objects.create(nombre="Vacante ranking", version=1)
    obligatorio = CriterioEvaluacion.objects.create(rubrica=rubrica, nombre="Django", descripcion="Experiencia Django", peso=Decimal("60"), obligatorio=True, orden=1)
    deseable = CriterioEvaluacion.objects.create(rubrica=rubrica, nombre="AWS", descripcion="Experiencia AWS", peso=Decimal("40"), obligatorio=False, orden=2)
    vacante = Vacante.objects.create(propietario=usuario, titulo="Backend", estado=EstadoVacante.EVALUANDO, rubrica=rubrica)
    ejecucion = EjecucionVacante.objects.create(vacante=vacante, numero=1, estado=EstadoEjecucion.PROCESANDO, total=cantidad)
    for indice in range(cantidad):
        documento = Documento.objects.create(
            origen=OrigenDocumento.MANUAL, nombre_original=f"candidato-{indice}.pdf", nombre_interno=f"candidato-{indice}.pdf",
            archivo=ContentFile(b"%PDF-test", name=f"candidato-{indice}.pdf"), mime_type="application/pdf",
            hash_sha256=f"{indice:064x}", tamano_bytes=9, estado=EstadoDocumento.ANALIZADO,
        )
        puntuacion = Decimal(100 - indice)
        sin_obligatorio = indice == 0
        analisis = AnalisisDocumento.objects.create(
            documento=documento, rubrica=rubrica, numero=1, estado=EstadoAnalisis.COMPLETADO,
            perfil={"nombre": f"Candidato {indice}"}, resumen=f"Resumen {indice}", fortalezas=["Python"], brechas=[],
            resultados_criterios=[
                {"criterio_id": obligatorio.id, "puntuacion": 0 if sin_obligatorio else 90, "evidencia": "" if sin_obligatorio else "Proyecto Django"},
                {"criterio_id": deseable.id, "puntuacion": 80, "evidencia": "AWS"},
            ], puntuacion=puntuacion, modelo="test",
        )
        EvaluacionVacante.objects.create(ejecucion=ejecucion, documento=documento, analisis=analisis, estado=EstadoEvaluacion.COMPLETADA)
    _actualizar_ejecucion(ejecucion.id)
    return usuario, vacante, ejecucion


def test_ranking_top_diez_evidencia_obligatorios_y_pdf_protegido():
    usuario, vacante, ejecucion = escenario_ranking()
    cliente = APIClient(); cliente.force_authenticate(usuario)
    respuesta = cliente.get(f"/api/vacantes/{vacante.id}/ejecuciones/{ejecucion.id}/ranking/")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["count"] == 12 and len(datos["results"]) == 10
    assert datos["results"][0]["nombre"] == "Candidato 0"
    assert datos["results"][0]["obligatorios_no_demostrados"][0]["nombre"] == "Django"
    documento_id = datos["results"][0]["documento"]
    ruta = f"/api/documentos/{documento_id}/archivo/"
    assert datos["results"][0]["pdf_url"].endswith(ruta)
    assert cliente.get(ruta).status_code == 200
    assert APIClient().get(ruta).status_code in {401, 403}


def test_resumen_final_es_unico_y_no_rechaza_candidatos():
    usuario, vacante, ejecucion = escenario_ranking(2)
    mensaje = vacante.mensajes.get(rol=RolMensaje.AGENTE, datos__tipo="RESULTADO_EJECUCION")
    mensaje.contenido = "Resumen obsoleto"
    mensaje.save(update_fields=["contenido"])
    _actualizar_ejecucion(ejecucion.id)
    mensajes = vacante.mensajes.filter(rol=RolMensaje.AGENTE, datos__tipo="RESULTADO_EJECUCION")
    assert mensajes.count() == 1
    assert "Candidato 0" in mensajes.get().contenido
    assert "no constituye una decisión" in mensajes.get().contenido
    cliente = APIClient(); cliente.force_authenticate(usuario)
    assert cliente.get(f"/api/vacantes/{vacante.id}/ejecuciones/{ejecucion.id}/ranking/").json()["count"] == 2


def test_ranking_aislado_por_usuario():
    _, vacante, ejecucion = escenario_ranking(1)
    otro = get_user_model().objects.create_user("otro-ranking")
    cliente = APIClient(); cliente.force_authenticate(otro)
    respuesta = cliente.get(f"/api/vacantes/{vacante.id}/ejecuciones/{ejecucion.id}/ranking/")
    assert respuesta.status_code == 200 and respuesta.json()["count"] == 0
