from django.conf import settings
from django.db import models

from analisis.models import RubricaEvaluacion
from documentos.models import Documento


class EstadoVacante(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    ESPERANDO_CONFIRMACION = "ESPERANDO_CONFIRMACION", "Esperando confirmación"
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    EVALUANDO = "EVALUANDO", "Evaluando"
    COMPLETADA = "COMPLETADA", "Completada"
    ERROR = "ERROR", "Error"


class RolMensaje(models.TextChoices):
    RECLUTADOR = "RECLUTADOR", "Reclutador"
    AGENTE = "AGENTE", "Agente"


class EstadoTarea(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    PROCESANDO = "PROCESANDO", "Procesando"
    COMPLETADA = "COMPLETADA", "Completada"
    ERROR = "ERROR", "Error"


class EstadoEjecucion(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    PROCESANDO = "PROCESANDO", "Procesando"
    COMPLETADA = "COMPLETADA", "Completada"
    PARCIAL = "PARCIAL", "Parcial"
    ERROR = "ERROR", "Error"


class EstadoEvaluacion(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    PROCESANDO = "PROCESANDO", "Procesando"
    COMPLETADA = "COMPLETADA", "Completada"
    SIN_TEXTO = "SIN_TEXTO", "Sin texto"
    ERROR = "ERROR", "Error"


class Vacante(models.Model):
    propietario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vacantes")
    titulo = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=30, choices=EstadoVacante.choices, default=EstadoVacante.BORRADOR, db_index=True)
    rubrica = models.ForeignKey(RubricaEvaluacion, on_delete=models.PROTECT, null=True, blank=True, related_name="vacantes")
    propuesta = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.titulo or f"Vacante #{self.pk}"


class MensajeVacante(models.Model):
    vacante = models.ForeignKey(Vacante, on_delete=models.CASCADE, related_name="mensajes")
    rol = models.CharField(max_length=20, choices=RolMensaje.choices)
    contenido = models.TextField()
    datos = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.vacante_id} · {self.rol}"


class TareaConversacion(models.Model):
    vacante = models.ForeignKey(Vacante, on_delete=models.CASCADE, related_name="tareas_conversacion")
    mensaje = models.OneToOneField(MensajeVacante, on_delete=models.CASCADE, related_name="tarea")
    estado = models.CharField(max_length=20, choices=EstadoTarea.choices, default=EstadoTarea.PENDIENTE, db_index=True)
    intentos = models.PositiveSmallIntegerField(default=0)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]


class EjecucionVacante(models.Model):
    vacante = models.ForeignKey(Vacante, on_delete=models.CASCADE, related_name="ejecuciones")
    numero = models.PositiveIntegerField()
    estado = models.CharField(max_length=20, choices=EstadoEjecucion.choices, default=EstadoEjecucion.PENDIENTE, db_index=True)
    total = models.PositiveIntegerField(default=0)
    completados = models.PositiveIntegerField(default=0)
    sin_texto = models.PositiveIntegerField(default=0)
    errores = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["vacante", "numero"], name="ejecucion_vacante_numero_unico")]


class EvaluacionVacante(models.Model):
    ejecucion = models.ForeignKey(EjecucionVacante, on_delete=models.CASCADE, related_name="evaluaciones")
    documento = models.ForeignKey(Documento, on_delete=models.PROTECT, related_name="evaluaciones_vacante")
    analisis = models.OneToOneField("analisis.AnalisisDocumento", on_delete=models.PROTECT, null=True, blank=True, related_name="evaluacion_vacante")
    estado = models.CharField(max_length=20, choices=EstadoEvaluacion.choices, default=EstadoEvaluacion.PENDIENTE, db_index=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["ejecucion", "documento"], name="evaluacion_ejecucion_documento_unica")]
