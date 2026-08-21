import json
from copy import deepcopy
from json import JSONDecodeError
from typing import Any

import requests
from django.conf import settings


class RespuestaOllamaInvalida(Exception):
    pass


SCHEMA = {
    "type": "object",
    "properties": {
        "perfil": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "maxLength": 200},
                "correo": {"type": "string", "maxLength": 200},
                "telefono": {"type": "string", "maxLength": 80},
                "habilidades": {"type": "array", "maxItems": 10, "items": {"type": "string", "maxLength": 100}},
                "experiencia": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 160}},
                "educacion": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 140}},
            },
            "required": ["nombre", "correo", "telefono", "habilidades", "experiencia", "educacion"],
        },
        "resumen": {"type": "string", "maxLength": 600},
        "fortalezas": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 160}},
        "brechas": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 160}},
        "criterios": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterio_id": {"type": "integer"},
                    "puntuacion": {"type": "number", "minimum": 0, "maximum": 100},
                    "evidencia": {"type": "string", "maxLength": 240},
                },
                "required": ["criterio_id", "puntuacion", "evidencia"],
            },
        },
    },
    "required": ["perfil", "resumen", "fortalezas", "brechas", "criterios"],
}


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS

    def evaluar(self, texto: str, criterios: list[dict[str, Any]]) -> dict:
        prompt = self._prompt(texto, criterios)
        schema = deepcopy(SCHEMA)
        schema_criterios = schema["properties"]["criterios"]
        schema_criterios["minItems"] = len(criterios)
        schema_criterios["maxItems"] = len(criterios)
        schema_criterios["items"]["properties"]["criterio_id"]["enum"] = [item["id"] for item in criterios]

        ultimo_error: Exception | None = None
        for _ in range(2):
            try:
                contenido = self._llamar_modelo(prompt, schema)
                datos = self._cargar_json(contenido)
                self._validar(datos, criterios)
                return datos
            except JSONDecodeError as exc:
                ultimo_error = exc
                try:
                    datos = self._reparar_json(contenido, schema)
                    self._validar(datos, criterios)
                    return datos
                except (requests.RequestException, ValueError, TypeError, RespuestaOllamaInvalida, JSONDecodeError) as reparacion_exc:
                    ultimo_error = reparacion_exc
            except (requests.RequestException, ValueError, TypeError, RespuestaOllamaInvalida) as exc:
                ultimo_error = exc

        raise RespuestaOllamaInvalida(f"Ollama no devolvio una respuesta valida: {ultimo_error}")

    def _llamar_modelo(self, prompt: str, schema: dict[str, Any]) -> str:
        respuesta = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                # Gemma 4 puede consumir todo num_predict en razonamiento interno
                # y dejar content vacio. Las evaluaciones solo necesitan el JSON.
                "think": False,
                "format": schema,
                "options": {"temperature": 0, "num_predict": 1500, "num_ctx": 4096, "num_thread": 4},
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=self.timeout,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
        mensaje = datos.get("message", {})
        contenido = mensaje.get("content", "")
        if not contenido or not contenido.strip():
            motivo = datos.get("done_reason", "desconocido")
            tokens = datos.get("eval_count", 0)
            razonamiento = len(mensaje.get("thinking", ""))
            raise RespuestaOllamaInvalida(
                "Ollama devolvio contenido vacio "
                f"(motivo={motivo}, tokens={tokens}, caracteres_razonamiento={razonamiento})"
            )
        if datos.get("done_reason") == "length":
            raise RespuestaOllamaInvalida(
                f"Ollama trunco la respuesta al alcanzar {datos.get('eval_count', 0)} tokens"
            )
        return contenido

    def _reparar_json(self, contenido: str, schema: dict[str, Any]) -> dict:
        if not contenido or not contenido.strip():
            raise RespuestaOllamaInvalida("No hay contenido para reparar")
        reparado = self._llamar_modelo(
            (
                "Repara la siguiente respuesta para que sea JSON valido y cumpla exactamente el esquema solicitado. "
                "No agregues explicaciones, markdown ni texto fuera del JSON. Conserva los datos originales cuando sea posible. "
                "No uses ni infieras edad, genero, fotografia, estado civil, nacionalidad, domicilio, salud, religion "
                "u otros atributos sensibles para ninguna puntuacion.\n\n"
                f"RESPUESTA A REPARAR:\n{contenido[:12000]}"
            ),
            schema,
        )
        return self._cargar_json(reparado)

    @staticmethod
    def _cargar_json(contenido: str) -> dict:
        contenido = (contenido or "").strip()
        if contenido.startswith("```"):
            partes = contenido.split("```")
            contenido = next((parte.strip() for parte in partes if "{" in parte and "}" in parte), contenido)
            if contenido.lower().startswith("json"):
                contenido = contenido[4:].strip()
        try:
            return json.loads(contenido)
        except JSONDecodeError:
            inicio = contenido.find("{")
            fin = contenido.rfind("}")
            if inicio != -1 and fin != -1 and fin > inicio:
                return json.loads(contenido[inicio:fin + 1])
            raise

    @staticmethod
    def _prompt(texto: str, criterios: list[dict[str, Any]]) -> str:
        criterios_sin_pesos = [
            {clave: valor for clave, valor in criterio.items() if clave in {"id", "nombre", "descripcion", "obligatorio"}}
            for criterio in criterios
        ]
        return (
            "Analiza el curriculum usando exclusivamente la evidencia del texto. Responde de forma concisa y devuelve el JSON solicitado. "
            "No uses ni infieras edad, genero, fotografia, estado civil, nacionalidad, domicilio, salud, religion "
            "u otros atributos sensibles para ninguna puntuacion. Califica CADA criterio de forma independiente entre 0 y 100; "
            "la puntuacion no es un peso ni un porcentaje del total. Si no existe evidencia, asigna 0 y explicalo.\n\n"
            f"CRITERIOS:\n{json.dumps(criterios_sin_pesos, ensure_ascii=False)}\n\n"
            f"CURRICULUM:\n{texto[:18000]}"
        )

    @staticmethod
    def _validar(datos: dict, criterios: list[dict[str, Any]]) -> None:
        if not isinstance(datos, dict):
            raise RespuestaOllamaInvalida("La respuesta no es un objeto")
        requeridos = {"perfil", "resumen", "fortalezas", "brechas", "criterios"}
        if not requeridos.issubset(datos):
            raise RespuestaOllamaInvalida("Faltan campos requeridos")
        ids_esperados = {item["id"] for item in criterios}
        resultados = datos.get("criterios")
        if not isinstance(resultados, list) or {item.get("criterio_id") for item in resultados} != ids_esperados:
            raise RespuestaOllamaInvalida("Los criterios de la respuesta no coinciden con la rubrica")
        for item in resultados:
            puntuacion = item.get("puntuacion")
            if not isinstance(puntuacion, (int, float)) or not 0 <= puntuacion <= 100 or not isinstance(item.get("evidencia"), str):
                raise RespuestaOllamaInvalida("Resultado de criterio invalido")
