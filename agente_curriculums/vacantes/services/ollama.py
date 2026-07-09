import json
from typing import Any

import requests
from django.conf import settings


class InterpretacionInvalida(Exception):
    pass


SCHEMA_VACANTE = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string", "maxLength": 200},
        "resumen": {"type": "string", "maxLength": 1000},
        "preguntas": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 240}},
        "criterios": {
            "type": "array", "minItems": 3, "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "maxLength": 150},
                    "descripcion": {"type": "string", "maxLength": 500},
                    "peso": {"type": "number", "exclusiveMinimum": 0},
                    "obligatorio": {"type": "boolean"},
                },
                "required": ["nombre", "descripcion", "peso", "obligatorio"],
            },
        },
    },
    "required": ["titulo", "resumen", "preguntas", "criterios"],
}


class OllamaVacanteClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS

    def interpretar(self, mensajes: list[dict[str, Any]], propuesta_actual: dict | None = None) -> dict:
        prompt = self._prompt(mensajes, propuesta_actual)
        ultimo_error = None
        for _ in range(2):
            try:
                respuesta = requests.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model, "stream": False, "format": SCHEMA_VACANTE,
                        "options": {"temperature": 0, "num_predict": 1000, "num_ctx": 4096, "num_thread": 4},
                        "messages": [{"role": "user", "content": prompt}],
                    }, timeout=self.timeout,
                )
                respuesta.raise_for_status()
                datos = json.loads(respuesta.json().get("message", {}).get("content", ""))
                self._validar(datos)
                return datos
            except (requests.RequestException, ValueError, TypeError, InterpretacionInvalida) as exc:
                ultimo_error = exc
        raise InterpretacionInvalida(f"Ollama no devolvió una propuesta válida: {ultimo_error}")

    @staticmethod
    def _prompt(mensajes, propuesta_actual):
        historial = [{"rol": item["rol"], "contenido": item["contenido"]} for item in mensajes[-12:]]
        return (
            "Convierte la conversación de reclutamiento en una propuesta de vacante. Usa de 3 a 8 criterios profesionales. "
            "Respeta literalmente qué requisitos declaró el reclutador como obligatorios y cuáles como deseables: nunca conviertas "
            "un requisito deseable en obligatorio. Las preguntas deben estar dirigidas al reclutador para aclarar la vacante, no al candidato. "
            "No crees criterios ni preguntas sobre edad, género, sexo, fotografía, estado civil, nacionalidad, domicilio, salud, "
            "religión, embarazo, discapacidad u otros atributos sensibles. Los pesos deben ser positivos y aproximadamente sumar 100; "
            "Django realizará el ajuste exacto. Si falta información, incluye preguntas breves, pero entrega una propuesta utilizable.\n\n"
            f"PROPUESTA ACTUAL:\n{json.dumps(propuesta_actual or {}, ensure_ascii=False)}\n\n"
            f"CONVERSACIÓN:\n{json.dumps(historial, ensure_ascii=False)}"
        )

    @staticmethod
    def _validar(datos):
        if not isinstance(datos, dict) or not {"titulo", "resumen", "preguntas", "criterios"}.issubset(datos):
            raise InterpretacionInvalida("Faltan campos requeridos")
        criterios = datos.get("criterios")
        if not isinstance(criterios, list) or not 3 <= len(criterios) <= 8:
            raise InterpretacionInvalida("La propuesta debe contener de 3 a 8 criterios")
        for criterio in criterios:
            if not isinstance(criterio, dict) or not {"nombre", "descripcion", "peso", "obligatorio"}.issubset(criterio):
                raise InterpretacionInvalida("Criterio incompleto")
            if not isinstance(criterio["peso"], (int, float)) or criterio["peso"] <= 0:
                raise InterpretacionInvalida("Peso inválido")
