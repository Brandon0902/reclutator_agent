import json
from unittest.mock import Mock

import pytest

from analisis.services.ollama import OllamaClient, RespuestaOllamaInvalida


def respuesta_valida():
    return {
        "perfil": {"nombre": "Ana", "correo": "", "telefono": "", "habilidades": [], "experiencia": [], "educacion": []},
        "resumen": "Coincide parcialmente.",
        "fortalezas": ["Experiencia relevante"],
        "brechas": [],
        "criterios": [{"criterio_id": 1, "puntuacion": 80, "evidencia": "Menciona experiencia relacionada."}],
    }


def criterios():
    return [{"id": 1, "nombre": "Experiencia", "descripcion": "Experiencia requerida", "obligatorio": True}]


def test_carga_json_directo_y_extraido_de_markdown():
    datos = respuesta_valida()
    assert OllamaClient._cargar_json(json.dumps(datos)) == datos
    assert OllamaClient._cargar_json(f"```json\n{json.dumps(datos)}\n```") == datos
    assert OllamaClient._cargar_json(f"Texto antes\n{json.dumps(datos)}\nTexto despues") == datos


def test_evalua_repara_json_invalido_con_segunda_llamada(settings):
    settings.OLLAMA_BASE_URL = "http://ollama.test"
    settings.OLLAMA_MODEL = "modelo-test"
    settings.OLLAMA_TIMEOUT_SECONDS = 1

    cliente = OllamaClient()
    cliente._llamar_modelo = Mock(side_effect=["{json roto", json.dumps(respuesta_valida())])

    resultado = cliente.evaluar("texto de cv", criterios())

    assert resultado["criterios"][0]["puntuacion"] == 80
    assert cliente._llamar_modelo.call_count == 2


def test_rechaza_respuesta_reparada_que_no_cumple_criterios(settings):
    settings.OLLAMA_BASE_URL = "http://ollama.test"
    settings.OLLAMA_MODEL = "modelo-test"
    settings.OLLAMA_TIMEOUT_SECONDS = 1

    invalida = respuesta_valida()
    invalida["criterios"] = [{"criterio_id": 999, "puntuacion": 80, "evidencia": "No coincide"}]
    cliente = OllamaClient()
    cliente._llamar_modelo = Mock(side_effect=["{json roto", json.dumps(invalida), "{json roto", json.dumps(invalida)])

    with pytest.raises(RespuestaOllamaInvalida):
        cliente.evaluar("texto de cv", criterios())


def test_llamada_desactiva_razonamiento_y_acepta_json(settings, monkeypatch):
    settings.OLLAMA_BASE_URL = "http://ollama.test"
    settings.OLLAMA_MODEL = "modelo-test"
    settings.OLLAMA_TIMEOUT_SECONDS = 1
    respuesta = Mock()
    respuesta.raise_for_status.return_value = None
    respuesta.json.return_value = {
        "done_reason": "stop",
        "eval_count": 100,
        "message": {"content": json.dumps(respuesta_valida())},
    }
    post = Mock(return_value=respuesta)
    monkeypatch.setattr("analisis.services.ollama.requests.post", post)

    contenido = OllamaClient()._llamar_modelo("prompt", {"type": "object"})

    assert json.loads(contenido) == respuesta_valida()
    payload = post.call_args.kwargs["json"]
    assert payload["think"] is False
    assert payload["options"]["num_predict"] == 1500


def test_llamada_reporta_respuesta_vacia_con_diagnostico(settings, monkeypatch):
    settings.OLLAMA_BASE_URL = "http://ollama.test"
    settings.OLLAMA_MODEL = "modelo-test"
    settings.OLLAMA_TIMEOUT_SECONDS = 1
    respuesta = Mock()
    respuesta.raise_for_status.return_value = None
    respuesta.json.return_value = {
        "done_reason": "length",
        "eval_count": 750,
        "message": {"content": "", "thinking": "razonamiento interno"},
    }
    monkeypatch.setattr("analisis.services.ollama.requests.post", Mock(return_value=respuesta))

    with pytest.raises(RespuestaOllamaInvalida, match=r"contenido vacio.*motivo=length.*tokens=750"):
        OllamaClient()._llamar_modelo("prompt", {"type": "object"})
