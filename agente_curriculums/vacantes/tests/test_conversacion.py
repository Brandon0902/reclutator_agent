from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from vacantes.models import EstadoTarea, EstadoVacante, MensajeVacante, RolMensaje, TareaConversacion, Vacante
from vacantes.services.conversacion import aplicar_obligatoriedad_explicita, confirmar_vacante, incorporar_requisitos_explicitos, normalizar_propuesta, procesar_tarea_conversacion
from vacantes.services.ollama import InterpretacionInvalida, OllamaVacanteClient


pytestmark = pytest.mark.django_db


def propuesta(**cambios):
    datos = {
        "titulo": "Desarrollador Python",
        "resumen": "Desarrollo de aplicaciones web",
        "preguntas": ["¿Qué nivel de inglés se requiere?"],
        "criterios": [
            {"nombre": "Python", "descripcion": "Experiencia comprobable", "peso": 5, "obligatorio": True},
            {"nombre": "Django", "descripcion": "Desarrollo web", "peso": 3, "obligatorio": True},
            {"nombre": "AWS", "descripcion": "Servicios en nube", "peso": 2, "obligatorio": False},
        ],
    }
    datos.update(cambios)
    return datos


def crear_tarea():
    usuario = get_user_model().objects.create_user("reclutador")
    vacante = Vacante.objects.create(propietario=usuario)
    mensaje = MensajeVacante.objects.create(vacante=vacante, rol=RolMensaje.RECLUTADOR, contenido="Busco Python")
    return TareaConversacion.objects.create(vacante=vacante, mensaje=mensaje)


def test_normaliza_pesos_y_rechaza_atributos_sensibles():
    datos = normalizar_propuesta(propuesta())
    assert sum(Decimal(item["peso"]) for item in datos["criterios"]) == Decimal("100")
    sensible = propuesta()
    sensible["criterios"][0]["nombre"] = "Edad"
    with pytest.raises(ValueError, match="sensibles"):
        normalizar_propuesta(sensible)


def test_declaracion_deseable_del_reclutador_prevalece_sobre_gemma():
    datos = propuesta()
    datos["criterios"][2]["obligatorio"] = True
    normalizada = normalizar_propuesta(datos)
    mensajes = [
        {"rol": RolMensaje.RECLUTADOR, "contenido": "Python y Django son obligatorios."},
        {"rol": RolMensaje.RECLUTADOR, "contenido": "AWS e inglés son deseables, no obligatorios."},
    ]
    corregida = aplicar_obligatoriedad_explicita(normalizada, mensajes)
    assert next(item for item in corregida["criterios"] if item["nombre"] == "AWS")["obligatorio"] is False


def test_incorpora_requisito_explicito_omitido_por_gemma():
    datos = propuesta()
    datos["criterios"] = datos["criterios"][:2]
    datos["criterios"].append({"nombre": "Logros", "descripcion": "Resultados", "peso": 2, "obligatorio": False})
    mensajes = [{"rol": RolMensaje.RECLUTADOR, "contenido": "Python y Django son obligatorios. AWS e inglés son deseables, no obligatorios."}]
    completada = incorporar_requisitos_explicitos(datos, mensajes)
    nombres = [item["nombre"].casefold() for item in completada["criterios"]]
    assert "aws" in nombres and "inglés" in nombres
    normalizada = aplicar_obligatoriedad_explicita(normalizar_propuesta(completada), mensajes)
    assert all(not item["obligatorio"] for item in normalizada["criterios"] if item["nombre"].casefold() in {"aws", "inglés"})


def test_procesa_turno_confirma_rubrica_y_la_vuelve_inmutable():
    tarea = crear_tarea()
    cliente = Mock()
    cliente.interpretar.return_value = propuesta()
    resultado = procesar_tarea_conversacion(tarea.id, cliente)
    assert resultado.estado == EstadoTarea.COMPLETADA
    tarea.vacante.refresh_from_db()
    assert tarea.vacante.estado == EstadoVacante.ESPERANDO_CONFIRMACION
    assert tarea.vacante.mensajes.filter(rol=RolMensaje.AGENTE).exists()
    confirmar_vacante(tarea.vacante)
    tarea.vacante.refresh_from_db()
    assert tarea.vacante.estado == EstadoVacante.CONFIRMADA
    assert tarea.vacante.rubrica.criterios.count() == 3
    assert sum(c.peso for c in tarea.vacante.rubrica.criterios.all()) == Decimal("100")
    criterio = tarea.vacante.rubrica.criterios.first()
    criterio.peso = 1
    with pytest.raises(ValidationError):
        criterio.save()


def test_error_recuperable_de_interpretacion_se_registra():
    tarea = crear_tarea()
    cliente = Mock()
    cliente.interpretar.side_effect = InterpretacionInvalida("servicio caído")
    resultado = procesar_tarea_conversacion(tarea.id, cliente)
    assert resultado.estado == EstadoTarea.ERROR
    assert "servicio caído" in resultado.error
    tarea.vacante.refresh_from_db()
    assert tarea.vacante.estado == EstadoVacante.ERROR


@patch("vacantes.services.ollama.requests.post")
def test_ollama_reintenta_json_invalido(mock_post, settings):
    invalida = Mock(); invalida.raise_for_status.return_value = None; invalida.json.return_value = {"message": {"content": "no-json"}}
    valida = Mock(); valida.raise_for_status.return_value = None; valida.json.return_value = {"message": {"content": __import__("json").dumps(propuesta())}}
    mock_post.side_effect = [invalida, valida]
    resultado = OllamaVacanteClient().interpretar([{"rol": "RECLUTADOR", "contenido": "Python"}])
    assert resultado["titulo"] == "Desarrollador Python"
    assert mock_post.call_count == 2
    prompt = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "nunca conviertas" in prompt and "dirigidas al reclutador" in prompt


def test_api_confirma_solo_propuesta_propia_y_pendiente():
    tarea = crear_tarea()
    procesar_tarea_conversacion(tarea.id, Mock(interpretar=Mock(return_value=propuesta())))
    cliente = APIClient(); cliente.force_authenticate(tarea.vacante.propietario)
    assert cliente.post(f"/api/vacantes/{tarea.vacante_id}/confirmar/", {}, format="json").status_code == 200
    assert cliente.post(f"/api/vacantes/{tarea.vacante_id}/confirmar/", {}, format="json").status_code == 400


def test_rubrica_de_vacante_es_privada_para_otro_usuario():
    tarea = crear_tarea()
    procesar_tarea_conversacion(tarea.id, Mock(interpretar=Mock(return_value=propuesta())))
    confirmar_vacante(tarea.vacante)
    tarea.vacante.refresh_from_db()
    otro = get_user_model().objects.create_user("otro-rubrica")
    cliente = APIClient(); cliente.force_authenticate(otro)
    assert cliente.get(f"/api/rubricas/{tarea.vacante.rubrica_id}/").status_code == 404
