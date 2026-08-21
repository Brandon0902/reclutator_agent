import uuid
from pathlib import Path
from django.db import models
from django.utils import timezone

class OrigenDocumento(models.TextChoices):
    MANUAL = "MANUAL", "Carga manual"
    OUTLOOK = "OUTLOOK", "Outlook"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    IMAP = "IMAP", "Correo IMAP"
    FORMULARIO_WEB = "FORMULARIO_WEB", "Formulario web"
class EstadoDocumento(models.TextChoices):
    RECIBIDO = "RECIBIDO", "Recibido"
    PENDIENTE_ANALISIS = "PENDIENTE_ANALISIS", "Pendiente de análisis"
    DUPLICADO = "DUPLICADO", "Duplicado"
    FORMATO_INVALIDO = "FORMATO_INVALIDO", "Formato inválido"
    ERROR_DESCARGA = "ERROR_DESCARGA", "Error de descarga"
    ERROR_ALMACENAMIENTO = "ERROR_ALMACENAMIENTO", "Error de almacenamiento"
    EN_ANALISIS = "EN_ANALISIS", "En análisis"
    ANALIZADO = "ANALIZADO", "Analizado"
    ERROR_ANALISIS = "ERROR_ANALISIS", "Error de análisis"
    SIN_TEXTO = "SIN_TEXTO", "Sin texto analizable"
def curriculum_upload_to(instance, filename):
    now = timezone.now()
    return f"curriculums/{now:%Y/%m}/{uuid.uuid4()}.pdf"
class Documento(models.Model):
    origen = models.CharField(max_length=20, choices=OrigenDocumento.choices)
    id_mensaje_origen = models.CharField(max_length=255, blank=True)
    nombre_original = models.CharField(max_length=255)
    nombre_interno = models.CharField(max_length=255)
    archivo = models.FileField(upload_to=curriculum_upload_to)
    mime_type = models.CharField(max_length=100, default="application/pdf")
    hash_sha256 = models.CharField(max_length=64, unique=True)
    tamano_bytes = models.PositiveBigIntegerField()
    remitente = models.CharField(max_length=255, blank=True)
    correo = models.EmailField(blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    fecha_recepcion = models.DateTimeField(default=timezone.now, db_index=True)
    estado = models.CharField(max_length=30, choices=EstadoDocumento.choices, default=EstadoDocumento.PENDIENTE_ANALISIS, db_index=True)
    error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["-fecha_recepcion"]
    def __str__(self): return self.nombre_original
class IntentoRecepcionDocumento(models.Model):
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="intentos")
    origen = models.CharField(max_length=20, choices=OrigenDocumento.choices)
    id_mensaje_origen = models.CharField(max_length=255, blank=True)
    remitente = models.CharField(max_length=255, blank=True)
    correo = models.EmailField(blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    fecha_recepcion = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
