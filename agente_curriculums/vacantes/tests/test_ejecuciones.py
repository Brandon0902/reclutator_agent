from decimal import Decimal
from unittest.mock import Mock

import fitz
import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework.test import APIClient

from analisis.models import CriterioEvaluacion, RubricaEvaluacion
from documentos.models import Documento, EstadoDocumento, OrigenDocumento
from vacantes.models import EstadoEjecucion, EstadoEvaluacion, EstadoVacante, Vacante
from vacantes.services.evaluacion import crear_ejecucion, procesar_evaluacion_vacante, reintentar_errores


pytestmark = pytest.mark.django_db


def pdf_texto(texto="Experiencia Python Django AWS " * 10):
    pdf = fitz.open(); pagina = pdf.new_page()
    for indice in range(10):
        pagina.insert_text((72, 72 + indice * 18), "Experiencia profesional Python Django AWS proyectos resultados")
    contenido = pdf.tobytes(); pdf.close(); return contenido


def documento(nombre, estado=EstadoDocumento.PENDIENTE_ANALISIS):
    contenido = pdf_texto()
    return Documento.objects.create(
        origen=OrigenDocumento.MANUAL, nombre_original=f"{nombre}.pdf", nombre_interno=f"{nombre}.pdf",
        archivo=ContentFile(contenido, name=f"{nombre}.pdf"), mime_type="application/pdf",
        hash_sha256=(nombre.encode().hex() + "0" * 64)[:64], tamano_bytes=len(contenido), estado=estado,
    )


def vacante_confirmada():
    usuario = get_user_model().objects.create_user("reclutador")
    rubrica = RubricaEvaluacion.objects.create(nombre="Vacante Python", version=1)
    CriterioEvaluacion.objects.create(rubrica=rubrica, nombre="Python", descripcion="Experiencia", peso=Decimal("100"), obligatorio=True)
    return Vacante.objects.create(propietario=usuario, titulo="Python", estado=EstadoVacante.CONFIRMADA, rubrica=rubrica)


def respuesta_ollama(criterio_id, puntuacion=80):
    return {
        "perfil": {"nombre": "Candidato", "correo": "", "telefono": "", "habilidades": ["Python"], "experiencia": ["Django"], "educacion": []},
        "resumen": "Perfil relevante", "fortalezas": ["Python"], "brechas": [],
        "criterios": [{"criterio_id": criterio_id, "puntuacion": puntuacion, "evidencia": "Experiencia Python"}],
    }


def test_crea_fotografia_y_procesa_evaluaciones_historicas():
    vacante = vacante_confirmada()
    documento("uno"); documento("dos", EstadoDocumento.SIN_TEXTO)
    ejecucion = crear_ejecucion(vacante)
    assert ejecucion.total == 2
    assert ejecucion.evaluaciones.filter(estado=EstadoEvaluacion.SIN_TEXTO).count() == 1
    evaluacion = ejecucion.evaluaciones.get(estado=EstadoEvaluacion.PENDIENTE)
    cliente = Mock(); cliente.evaluar.return_value = respuesta_ollama(vacante.rubrica.criterios.get().id)
    resultado = procesar_evaluacion_vacante(evaluacion.id, cliente)
    assert resultado.estado == EstadoEvaluacion.COMPLETADA
    ejecucion.refresh_from_db(); vacante.refresh_from_db()
    assert ejecucion.estado == EstadoEjecucion.COMPLETADA
    assert ejecucion.completados == 1 and ejecucion.sin_texto == 1
    assert vacante.estado == EstadoVacante.COMPLETADA
    documento("tres")
    assert ejecucion.evaluaciones.count() == 2
    segunda = crear_ejecucion(vacante)
    assert segunda.numero == 2 and segunda.total == 3


def test_bloqueo_logico_no_reprocesa_y_error_es_auditable():
    vacante = vacante_confirmada(); documento("uno")
    ejecucion = crear_ejecucion(vacante); evaluacion = ejecucion.evaluaciones.get()
    cliente = Mock(); cliente.evaluar.return_value = respuesta_ollama(vacante.rubrica.criterios.get().id)
    primero = procesar_evaluacion_vacante(evaluacion.id, cliente)
    segundo = procesar_evaluacion_vacante(evaluacion.id, cliente)
    assert primero.analisis_id == segundo.analisis_id
    assert cliente.evaluar.call_count == 1


def test_api_ejecucion_asincrona_y_aislada_por_propietario():
    vacante = vacante_confirmada(); documento("uno")
    cliente = APIClient(); cliente.force_authenticate(vacante.propietario)
    respuesta = cliente.post(f"/api/vacantes/{vacante.id}/evaluar/", {}, format="json")
    assert respuesta.status_code == 202
    ejecucion_id = respuesta.json()["id"]
    assert cliente.get(f"/api/vacantes/{vacante.id}/ejecuciones/").json()["count"] == 1
    assert cliente.get(f"/api/vacantes/{vacante.id}/ejecuciones/{ejecucion_id}/").status_code == 200
    otro = get_user_model().objects.create_user("otro")
    cliente.force_authenticate(otro)
    assert cliente.get(f"/api/vacantes/{vacante.id}/ejecuciones/{ejecucion_id}/").status_code == 404


def test_no_permite_evaluar_antes_de_confirmar_la_rubrica():
    usuario = get_user_model().objects.create_user("sin-confirmar")
    vacante = Vacante.objects.create(propietario=usuario, titulo="Vacante sin confirmar", estado=EstadoVacante.ESPERANDO_CONFIRMACION)
    cliente = APIClient(); cliente.force_authenticate(usuario)
    respuesta = cliente.post(f"/api/vacantes/{vacante.id}/evaluar/", {}, format="json")
    assert respuesta.status_code == 400
    assert "confirmada" in respuesta.json()["detail"]
    assert not vacante.ejecuciones.exists()


def test_reintento_manual_solo_reencola_errores():
    vacante = vacante_confirmada(); documento("uno"); documento("dos")
    ejecucion = crear_ejecucion(vacante)
    fallida = ejecucion.evaluaciones.first(); correcta = ejecucion.evaluaciones.last()
    fallida.estado = EstadoEvaluacion.ERROR; fallida.error = "timeout"; fallida.save()
    correcta.estado = EstadoEvaluacion.COMPLETADA; correcta.save()
    ejecucion.estado = EstadoEjecucion.PARCIAL; ejecucion.errores = 1; ejecucion.save()
    reintentar_errores(ejecucion)
    fallida.refresh_from_db(); correcta.refresh_from_db(); ejecucion.refresh_from_db()
    assert fallida.estado == EstadoEvaluacion.PENDIENTE and not fallida.error
    assert correcta.estado == EstadoEvaluacion.COMPLETADA
    assert ejecucion.estado == EstadoEjecucion.PENDIENTE
