"""Prefiltro local y auditable para evitar llamadas innecesarias a Ollama."""

import re
import unicodedata

from analisis.models import EstadoExtraccion
from analisis.services.extraccion import extraer_contenido


STOPWORDS = {
    "para", "como", "con", "por", "del", "las", "los", "una", "uno", "unos", "unas",
    "que", "sus", "entre", "sobre", "desde", "hasta", "esta", "este", "estas", "estos",
    "ser", "sea", "son", "tiene", "tener", "años", "ano", "mas", "muy", "sin", "una",
    "persona", "puesto", "perfil", "candidato", "candidata", "experiencia", "conocimiento",
    "habilidad", "habilidades", "capacidad", "manejo", "dominio", "deseable", "obligatorio",
    "responsable", "responsabilidades", "trabajo", "trabajar", "empresa", "equipo", "nivel",
    "tipo", "contar", "contar", "requisitos", "requisito", "busco", "buscar", "profesional",
}


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return texto.lower()


def _tokens(texto: str) -> set[str]:
    tokens = set()
    for token in re.findall(r"[a-z0-9][a-z0-9+#.-]{2,}", normalizar(texto)):
        if len(token) < 4 or token in STOPWORDS:
            continue
        tokens.add(token)
        if token.endswith("es") and len(token) > 6:
            tokens.add(token[:-2])
        elif token.endswith("s") and len(token) > 5:
            tokens.add(token[:-1])
    return tokens


def palabras_clave_vacante(vacante) -> set[str]:
    partes = [vacante.titulo, vacante.descripcion]
    if vacante.rubrica_id:
        partes.extend(
            criterio.nombre + " " + criterio.descripcion
            for criterio in vacante.rubrica.criterios.all()
        )
    propuesta = vacante.propuesta or {}
    palabras = propuesta.get("palabras_clave", []) or []
    if isinstance(palabras, str):
        palabras = [palabras]
    partes.extend(palabras)
    return _tokens(" ".join(str(parte) for parte in partes if parte))


def evaluar_relevancia(vacante, documento) -> tuple[bool, dict]:
    contenido = extraer_contenido(documento)
    if contenido.estado != EstadoExtraccion.COMPLETADO:
        return True, {"coincidencias": [], "palabras_clave": set(), "sin_texto": True}

    keywords = palabras_clave_vacante(vacante)
    texto_tokens = _tokens(contenido.texto)
    coincidencias = sorted(keywords.intersection(texto_tokens))

    # Política conservadora: si la vacante no produce suficientes términos,
    # no se filtra. Cuando sí los produce, solo se omite ante cero coincidencias.
    relevante = len(keywords) < 3 or bool(coincidencias)
    return relevante, {
        "coincidencias": coincidencias[:12],
        "palabras_clave": keywords,
        "sin_texto": False,
    }


def motivo_no_relevante(datos: dict) -> str:
    keywords = sorted(datos.get("palabras_clave", set()))[:8]
    referencia = ", ".join(keywords) or "sin términos específicos"
    return f"Omitido por prefiltro: no se encontraron coincidencias con la vacante. Términos considerados: {referencia}."
