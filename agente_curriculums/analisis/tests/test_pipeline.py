from decimal import Decimal
from unittest.mock import Mock, patch

import fitz
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APIClient

from analisis.models import (
    AnalisisDocumento, ContenidoExtraido, CriterioEvaluacion, EstadoAnalisis,
    EstadoExtraccion, RubricaEvaluacion,
)
from analisis.services.evaluacion import crear_analisis, procesar_analisis
from analisis.services.extraccion import extraer_contenido
from analisis.services.ollama import OllamaClient, RespuestaOllamaInvalida
from documentos.models import EstadoDocumento, OrigenDocumento
from documentos.services import DocumentoRecibido, recibir_documento


def crear_pdf(texto: str = "") -> bytes:
    pdf = fitz.open()
    pagina = pdf.new_page()
    if texto:
        pagina.insert_textbox(fitz.Rect(50, 50, 545, 790), texto, fontsize=10)
    contenido = pdf.tobytes()
    pdf.close()
    return contenido


def crear_documento(texto: str = "Experiencia profesional en Python y administración de sistemas. " * 10):
    return recibir_documento(DocumentoRecibido(
        origen=OrigenDocumento.MANUAL,
        nombre_original="cv.pdf",
        contenido=crear_pdf(texto),
        mime_type="application/pdf",
    ))[0]


def crear_rubrica(nombre="Técnica"):
    rubrica = RubricaEvaluacion.objects.create(nombre=nombre, version=1)
    CriterioEvaluacion.objects.create(rubrica=rubrica, nombre="Experiencia", descripcion="Experiencia relevante", peso=60, orden=1)
    CriterioEvaluacion.objects.create(rubrica=rubrica, nombre="Habilidades", descripcion="Habilidades demostradas", peso=40, orden=2)
    return rubrica


@pytest.mark.django_db
def test_extrae_texto_y_detecta_pdf_sin_texto():
    documento = crear_documento()
    contenido = extraer_contenido(documento)
    assert contenido.estado == EstadoExtraccion.COMPLETADO
    assert contenido.paginas == 1 and contenido.caracteres >= 100
    assert "Python" in contenido.texto

    vacio = crear_documento("")
    resultado = extraer_contenido(vacio)
    vacio.refresh_from_db()
    assert resultado.estado == EstadoExtraccion.SIN_TEXTO
    assert vacio.estado == EstadoDocumento.SIN_TEXTO


@pytest.mark.django_db
def test_rubrica_valida_pesos_unica_predeterminada_e_inmutabilidad():
    rubrica = crear_rubrica()
    rubrica.validar_pesos()
    assert RubricaEvaluacion.objects.filter(predeterminada=True).count() == 1
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RubricaEvaluacion.objects.create(nombre="Default B", predeterminada=True)

    documento = crear_documento()
    AnalisisDocumento.objects.create(documento=documento, rubrica=rubrica, numero=1, modelo="test")
    rubrica.descripcion = "Cambio no permitido"
    with pytest.raises(ValidationError):
        rubrica.save()
    criterio = rubrica.criterios.first()
    criterio.peso = 50
    with pytest.raises(ValidationError):
        criterio.save()


@pytest.mark.django_db
def test_evaluacion_calcula_score_determinista_y_no_se_repite():
    documento = crear_documento()
    rubrica = crear_rubrica()
    analisis = crear_analisis(documento, rubrica)
    cliente = Mock()
    cliente.evaluar.return_value = {
        "perfil": {"nombre": "Ana", "correo": "", "telefono": "", "habilidades": ["Python"], "experiencia": [], "educacion": []},
        "resumen": "Perfil técnico", "fortalezas": ["Python"], "brechas": ["Sin certificaciones"],
        "criterios": [
            {"criterio_id": rubrica.criterios.all()[0].id, "puntuacion": 80, "evidencia": "Experiencia en Python"},
            {"criterio_id": rubrica.criterios.all()[1].id, "puntuacion": 50, "evidencia": "Habilidad declarada"},
        ],
    }
    resultado = procesar_analisis(analisis.id, cliente)
    documento.refresh_from_db()
    assert resultado.estado == EstadoAnalisis.COMPLETADO
    assert resultado.puntuacion == Decimal("68.00")
    assert documento.estado == EstadoDocumento.ANALIZADO
    procesar_analisis(analisis.id, cliente)
    assert cliente.evaluar.call_count == 1


@patch("analisis.services.ollama.requests.post")
def test_ollama_reintenta_json_invalido_y_valida_criterios(mock_post, settings):
    settings.OLLAMA_BASE_URL = "http://ollama:11434"
    criterios = [{"id": 1, "nombre": "Experiencia", "descripcion": "", "peso": 100, "obligatorio": False}]
    invalida = Mock(); invalida.raise_for_status.return_value = None; invalida.json.return_value = {"message": {"content": "no-json"}}
    valida = Mock(); valida.raise_for_status.return_value = None; valida.json.return_value = {"message": {"content": '{"perfil":{"nombre":"","correo":"","telefono":"","habilidades":[],"experiencia":[],"educacion":[]},"resumen":"","fortalezas":[],"brechas":[],"criterios":[{"criterio_id":1,"puntuacion":70,"evidencia":"CV"}]}'}}
    mock_post.side_effect = [invalida, valida]
    respuesta = OllamaClient().evaluar("CV con edad 30 años", criterios)
    assert respuesta["criterios"][0]["puntuacion"] == 70
    assert mock_post.call_count == 2
    prompt = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "atributos sensibles" in prompt and "edad" in prompt
    assert '"peso"' not in prompt
    schema = mock_post.call_args.kwargs["json"]["format"]
    assert schema["properties"]["criterios"]["minItems"] == 1
    assert schema["properties"]["criterios"]["items"]["properties"]["criterio_id"]["enum"] == [1]


@pytest.mark.django_db
def test_api_rubricas_analisis_y_reanalisis(usuario):
    cliente = APIClient(); cliente.force_authenticate(usuario)
    respuesta = cliente.post("/api/rubricas/", {
        "nombre": "Soporte", "version": 1, "activa": True, "predeterminada": False,
        "descripcion": "", "criterios": [
            {"nombre": "Atención", "descripcion": "Experiencia", "peso": "70.00", "obligatorio": True, "orden": 1},
            {"nombre": "Sistemas", "descripcion": "Conocimientos", "peso": "30.00", "obligatorio": False, "orden": 2},
        ],
    }, format="json")
    assert respuesta.status_code == 201
    documento = crear_documento()
    solicitud = cliente.post(f"/api/documentos/{documento.id}/analizar/", {"rubrica": respuesta.json()["id"]}, format="json")
    assert solicitud.status_code == 201
    assert cliente.get(f"/api/documentos/{documento.id}/analisis/").json()["count"] == 1
    assert cliente.get("/api/analisis/?ordering=-puntuacion").status_code == 200


@pytest.mark.django_db
def test_api_protegida():
    assert APIClient().get("/api/rubricas/").status_code in (401, 403)
