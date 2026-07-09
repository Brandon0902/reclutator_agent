import re
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.utils import timezone

from analisis.models import CriterioEvaluacion, RubricaEvaluacion
from vacantes.models import EstadoTarea, EstadoVacante, MensajeVacante, RolMensaje, TareaConversacion, Vacante
from .ollama import OllamaVacanteClient


PATRON_SENSIBLE = re.compile(
    r"\b(edad|género|genero|sexo|fotografía|fotografia|estado civil|nacionalidad|domicilio|salud|religión|religion|embarazo|discapacidad)\b",
    re.IGNORECASE,
)


def normalizar_propuesta(datos: dict) -> dict:
    criterios = datos["criterios"]
    for criterio in criterios:
        if PATRON_SENSIBLE.search(f"{criterio['nombre']} {criterio['descripcion']}"):
            raise ValueError("La propuesta contiene un criterio basado en atributos sensibles")
    total = sum(Decimal(str(item["peso"])) for item in criterios)
    if total <= 0:
        raise ValueError("Los pesos deben ser positivos")
    pesos = [(Decimal(str(item["peso"])) * Decimal("100") / total).quantize(Decimal("0.01"), rounding=ROUND_DOWN) for item in criterios]
    restante = int(((Decimal("100") - sum(pesos)) * 100).to_integral_value())
    for indice in range(restante):
        pesos[indice % len(pesos)] += Decimal("0.01")
    salida = {"titulo": str(datos["titulo"]).strip()[:200], "resumen": str(datos["resumen"]).strip()[:1000], "preguntas": datos.get("preguntas", [])[:3], "criterios": []}
    for orden, (criterio, peso) in enumerate(zip(criterios, pesos), 1):
        salida["criterios"].append({
            "nombre": str(criterio["nombre"]).strip()[:150], "descripcion": str(criterio["descripcion"]).strip()[:500],
            "peso": str(peso), "obligatorio": bool(criterio["obligatorio"]), "orden": orden,
        })
    return salida


PALABRAS_COMUNES = {"experiencia", "técnica", "tecnica", "habilidades", "conocimiento", "nivel", "formal", "relevante", "currículum", "curriculum"}


def incorporar_requisitos_explicitos(datos: dict, mensajes: list[dict]) -> dict:
    requisitos = []
    for mensaje in mensajes:
        if mensaje.get("rol") != RolMensaje.RECLUTADOR:
            continue
        for frase in re.split(r"[.\n;]+", mensaje.get("contenido", "")):
            for coincidencia in re.finditer(r"(?:^|:)\s*([^:]+?)\s+son\s+(obligatori\w*|deseable\w*)", frase, re.IGNORECASE):
                grupo, tipo = coincidencia.groups()
                grupo = re.sub(r"^(únicamente|unicamente|solo|solamente)\s+", "", grupo.strip(), flags=re.IGNORECASE)
                for nombre in re.split(r"\s*,\s*|\s+y\s+|\s+e\s+", grupo, flags=re.IGNORECASE):
                    nombre = nombre.strip(" :,-")
                    if nombre:
                        requisitos.append((nombre, tipo.casefold().startswith("obligatori")))
    criterios = datos["criterios"]
    for nombre, obligatorio in requisitos:
        palabras = set(re.findall(r"[a-záéíóúñ0-9+#.]{3,}", nombre.casefold()))
        existe = any(palabras & set(re.findall(r"[a-záéíóúñ0-9+#.]{3,}", item["nombre"].casefold())) for item in criterios)
        if not existe and len(criterios) < 8:
            criterios.append({
                "nombre": nombre[:150], "descripcion": f"Evidencia profesional relacionada con {nombre}"[:500],
                "peso": 10, "obligatorio": obligatorio,
            })
    return datos


def aplicar_obligatoriedad_explicita(propuesta: dict, mensajes: list[dict]) -> dict:
    """Hace prevalecer la intención explícita del reclutador sobre la inferencia del modelo."""
    for mensaje in mensajes:
        if mensaje.get("rol") != RolMensaje.RECLUTADOR:
            continue
        for frase in re.split(r"[.\n;]+", mensaje.get("contenido", "")):
            frase_normalizada = frase.casefold()
            es_deseable = "deseable" in frase_normalizada or "no obligatorio" in frase_normalizada
            es_obligatorio = "obligatori" in frase_normalizada and not es_deseable
            if not (es_deseable or es_obligatorio):
                continue
            for criterio in propuesta["criterios"]:
                palabras = {
                    palabra for palabra in re.findall(r"[a-záéíóúñ0-9+#.]{3,}", criterio["nombre"].casefold())
                    if palabra not in PALABRAS_COMUNES
                }
                if palabras and any(palabra in frase_normalizada for palabra in palabras):
                    criterio["obligatorio"] = es_obligatorio
    return propuesta


def _contenido_respuesta(propuesta):
    criterios = ", ".join(f"{item['nombre']} ({item['peso']}%)" for item in propuesta["criterios"])
    preguntas = " ".join(propuesta["preguntas"])
    return f"Propongo evaluar: {criterios}. {preguntas}".strip()


def procesar_tarea_conversacion(tarea_id: int, cliente=None) -> TareaConversacion:
    with transaction.atomic():
        tarea = TareaConversacion.objects.select_for_update().select_related("vacante").get(pk=tarea_id)
        if tarea.estado != EstadoTarea.PENDIENTE:
            return tarea
        tarea.estado = EstadoTarea.PROCESANDO
        tarea.intentos += 1
        tarea.started_at = timezone.now()
        tarea.save(update_fields=["estado", "intentos", "started_at"])
    try:
        mensajes = list(tarea.vacante.mensajes.values("rol", "contenido"))
        datos = (cliente or OllamaVacanteClient()).interpretar(mensajes, tarea.vacante.propuesta)
        datos = incorporar_requisitos_explicitos(datos, mensajes)
        propuesta = aplicar_obligatoriedad_explicita(normalizar_propuesta(datos), mensajes)
        with transaction.atomic():
            vacante = Vacante.objects.select_for_update().get(pk=tarea.vacante_id)
            vacante.titulo = propuesta["titulo"]
            vacante.descripcion = propuesta["resumen"]
            vacante.propuesta = propuesta
            vacante.estado = EstadoVacante.ESPERANDO_CONFIRMACION
            vacante.error = ""
            vacante.save()
            MensajeVacante.objects.create(vacante=vacante, rol=RolMensaje.AGENTE, contenido=_contenido_respuesta(propuesta), datos=propuesta)
            tarea.estado = EstadoTarea.COMPLETADA
            tarea.completed_at = timezone.now()
            tarea.error = ""
            tarea.save(update_fields=["estado", "completed_at", "error"])
    except Exception as exc:
        tarea.estado = EstadoTarea.ERROR
        tarea.error = str(exc)[:2000]
        tarea.completed_at = timezone.now()
        tarea.save(update_fields=["estado", "error", "completed_at"])
        Vacante.objects.filter(pk=tarea.vacante_id).update(estado=EstadoVacante.ERROR, error=str(exc)[:2000])
    return tarea


@transaction.atomic
def confirmar_vacante(vacante: Vacante) -> Vacante:
    vacante = Vacante.objects.select_for_update().get(pk=vacante.pk)
    if vacante.estado != EstadoVacante.ESPERANDO_CONFIRMACION or not vacante.propuesta:
        raise ValueError("La vacante no tiene una propuesta pendiente de confirmación")
    propuesta = normalizar_propuesta(vacante.propuesta)
    rubrica = RubricaEvaluacion.objects.create(
        nombre=f"Vacante {vacante.pk}: {propuesta['titulo']}"[:150], descripcion=propuesta["resumen"], version=1, activa=True
    )
    CriterioEvaluacion.objects.bulk_create([
        CriterioEvaluacion(rubrica=rubrica, nombre=item["nombre"], descripcion=item["descripcion"], peso=Decimal(item["peso"]), obligatorio=item["obligatorio"], orden=item["orden"])
        for item in propuesta["criterios"]
    ])
    rubrica.validar_pesos()
    vacante.rubrica = rubrica
    vacante.estado = EstadoVacante.CONFIRMADA
    vacante.error = ""
    vacante.save(update_fields=["rubrica", "estado", "error", "updated_at"])
    return vacante
