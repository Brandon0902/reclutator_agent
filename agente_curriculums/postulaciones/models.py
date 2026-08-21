import hashlib
import hmac

from django.conf import settings
from django.db import models
from django.utils import timezone

from documentos.models import Documento
from vacantes.models import Vacante


class EstadoPostulacion(models.TextChoices):
    RECIBIDO = "RECIBIDO", "Recibido"
    EN_REVISION = "EN_REVISION", "En revisión"
    CONTACTADO = "CONTACTADO", "Contactado"
    DESCARTADO = "DESCARTADO", "Descartado"


class Candidato(models.Model):
    nombre_completo = models.CharField(max_length=200)
    telefono_whatsapp = models.CharField(max_length=50)
    correo = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["correo"], name="postulacio_correo_5c8ebf_idx"), models.Index(fields=["telefono_whatsapp"], name="postulacio_telefono_7c88d0_idx")]

    def __str__(self):
        return self.nombre_completo


class Postulacion(models.Model):
    candidato = models.ForeignKey(Candidato, on_delete=models.PROTECT, related_name="postulaciones")
    vacante = models.ForeignKey(Vacante, on_delete=models.PROTECT, null=True, blank=True, related_name="postulaciones")
    vacante_interes = models.CharField(max_length=200, db_index=True)
    documento = models.ForeignKey(Documento, on_delete=models.PROTECT, related_name="postulaciones")
    estado = models.CharField(max_length=20, choices=EstadoPostulacion.choices, default=EstadoPostulacion.RECIBIDO, db_index=True)
    consentimiento_datos = models.BooleanField(default=False)
    consentimiento_at = models.DateTimeField(default=timezone.now)
    consentimiento_version = models.CharField(max_length=30, default="v1")
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent_reducido = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["vacante", "documento"], name="postulacion_vacante_documento_unica")]
        indexes = [models.Index(fields=["vacante", "estado"], name="postulacio_vacante_4b9027_idx"), models.Index(fields=["vacante", "created_at"], name="postulacio_vacante_3e7736_idx")]

    def __str__(self):
        return f"{self.candidato} · {self.vacante or self.vacante_interes}"


class IntentoPostulacionPublica(models.Model):
    vacante = models.ForeignKey(Vacante, on_delete=models.CASCADE, null=True, blank=True, related_name="intentos_postulacion")
    ip_hash = models.CharField(max_length=64, blank=True)
    correo_hash = models.CharField(max_length=64, blank=True)
    telefono_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["ip_hash", "created_at"], name="post_int_ip_fecha_idx"),
            models.Index(fields=["correo_hash", "created_at"], name="post_int_correo_fecha_idx"),
            models.Index(fields=["telefono_hash", "created_at"], name="post_int_tel_fecha_idx"),
        ]


def hash_identifier(value, purpose):
    if not value:
        return ""
    payload = f"{purpose}:{value.strip().lower()}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def hash_ip(value):
    return hash_identifier(value, "ip")
