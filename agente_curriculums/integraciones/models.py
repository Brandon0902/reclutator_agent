from django.db import models
from django.utils import timezone
from documentos.models import OrigenDocumento
class MensajeExternoProcesado(models.Model):
    origen = models.CharField(max_length=20, choices=OrigenDocumento.choices)
    id_mensaje = models.CharField(max_length=255)
    fecha_procesamiento = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=30, default="PROCESADO")
    error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    class Meta: constraints = [models.UniqueConstraint(fields=["origen", "id_mensaje"], name="mensaje_origen_unico")]


class EstadoEventoWebhook(models.TextChoices):
    RECIBIDO = "RECIBIDO", "Recibido"
    IGNORADO = "IGNORADO", "Ignorado"
    PROCESADO = "PROCESADO", "Procesado"
    ERROR = "ERROR", "Error"


class EventoWebhook(models.Model):
    proveedor = models.CharField(max_length=20, default="WHATSAPP", db_index=True)
    payload_sha256 = models.CharField(max_length=64, unique=True)
    objeto = models.CharField(max_length=80, blank=True)
    estado = models.CharField(max_length=20, choices=EstadoEventoWebhook.choices, default=EstadoEventoWebhook.RECIBIDO, db_index=True)
    payload_sanitizado = models.JSONField(default=dict, blank=True)
    intentos = models.PositiveSmallIntegerField(default=0)
    error = models.TextField(blank=True)
    recibido_at = models.DateTimeField(auto_now_add=True, db_index=True)
    procesado_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-recibido_at"]


class DireccionMensajeWhatsApp(models.TextChoices):
    ENTRANTE = "ENTRANTE", "Entrante"
    SALIENTE = "SALIENTE", "Saliente"


class EstadoMensajeWhatsApp(models.TextChoices):
    RECIBIDO = "RECIBIDO", "Recibido"
    PENDIENTE = "PENDIENTE", "Pendiente"
    PROCESADO = "PROCESADO", "Procesado"
    IGNORADO = "IGNORADO", "Ignorado"
    ERROR = "ERROR", "Error"


class MensajeWhatsApp(models.Model):
    evento = models.ForeignKey(EventoWebhook, on_delete=models.PROTECT, related_name="mensajes")
    wamid = models.CharField(max_length=255, unique=True)
    direccion = models.CharField(max_length=12, choices=DireccionMensajeWhatsApp.choices, default=DireccionMensajeWhatsApp.ENTRANTE)
    tipo = models.CharField(max_length=30, db_index=True)
    wa_id = models.CharField(max_length=50, blank=True, db_index=True)
    nombre_perfil = models.CharField(max_length=255, blank=True)
    contenido_texto = models.TextField(blank=True)
    media_id = models.CharField(max_length=255, blank=True, db_index=True)
    documento = models.ForeignKey(
        "documentos.Documento", on_delete=models.PROTECT, null=True, blank=True,
        related_name="mensajes_whatsapp",
    )
    nombre_archivo = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    timestamp_meta = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=EstadoMensajeWhatsApp.choices, default=EstadoMensajeWhatsApp.RECIBIDO, db_index=True)
    error = models.TextField(blank=True)
    recibido_at = models.DateTimeField(auto_now_add=True)
    procesado_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["recibido_at", "id"]
        indexes = [models.Index(fields=["wa_id", "recibido_at"], name="wa_msg_contacto_fecha")]
