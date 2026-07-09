from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from documentos.models import Documento


class EstadoExtraccion(models.TextChoices):
    COMPLETADO = "COMPLETADO", "Completado"
    SIN_TEXTO = "SIN_TEXTO", "Sin texto"
    ERROR = "ERROR", "Error"


class EstadoAnalisis(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    PROCESANDO = "PROCESANDO", "Procesando"
    COMPLETADO = "COMPLETADO", "Completado"
    ERROR = "ERROR", "Error"
    SIN_TEXTO = "SIN_TEXTO", "Sin texto"


class RubricaEvaluacion(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    activa = models.BooleanField(default=True)
    predeterminada = models.BooleanField(default=False)
    clave_predeterminada = models.CharField(max_length=20, null=True, blank=True, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["nombre", "version"], name="rubrica_nombre_version_unica"),
        ]

    def __str__(self):
        return f"{self.nombre} v{self.version}"

    def save(self, *args, **kwargs):
        if self.pk and (self.analisis.exists() or self.vacantes.exists()):
            anterior = type(self).objects.get(pk=self.pk)
            campos = ("nombre", "descripcion", "version", "activa", "predeterminada")
            if any(getattr(anterior, campo) != getattr(self, campo) for campo in campos):
                raise ValidationError("Una rúbrica utilizada no puede modificarse; cree una versión nueva")
        self.clave_predeterminada = "DEFAULT" if self.predeterminada else None
        super().save(*args, **kwargs)

    def validar_pesos(self):
        total = self.criterios.aggregate(total=models.Sum("peso"))["total"] or Decimal("0")
        if total != Decimal("100"):
            raise ValidationError(f"Los pesos de la rúbrica deben sumar 100; suma actual: {total}")


class CriterioEvaluacion(models.Model):
    rubrica = models.ForeignKey(RubricaEvaluacion, on_delete=models.CASCADE, related_name="criterios")
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    peso = models.DecimalField(max_digits=5, decimal_places=2)
    obligatorio = models.BooleanField(default=False)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        constraints = [models.CheckConstraint(condition=Q(peso__gt=0) & Q(peso__lte=100), name="criterio_peso_valido")]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if self.rubrica_id and (self.rubrica.analisis.exists() or self.rubrica.vacantes.exists()):
            raise ValidationError("Los criterios de una rúbrica utilizada son inmutables")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.rubrica.analisis.exists() or self.rubrica.vacantes.exists():
            raise ValidationError("Los criterios de una rúbrica utilizada son inmutables")
        return super().delete(*args, **kwargs)


class ContenidoExtraido(models.Model):
    documento = models.OneToOneField(Documento, on_delete=models.CASCADE, related_name="contenido_extraido")
    texto = models.TextField(blank=True)
    paginas = models.PositiveIntegerField(default=0)
    caracteres = models.PositiveIntegerField(default=0)
    version_extractor = models.CharField(max_length=30, default="pymupdf-v1")
    estado = models.CharField(max_length=20, choices=EstadoExtraccion.choices)
    error = models.TextField(blank=True)
    extracted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Texto de {self.documento}"


class AnalisisDocumento(models.Model):
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="analisis")
    rubrica = models.ForeignKey(RubricaEvaluacion, on_delete=models.PROTECT, related_name="analisis")
    numero = models.PositiveIntegerField()
    estado = models.CharField(max_length=20, choices=EstadoAnalisis.choices, default=EstadoAnalisis.PENDIENTE, db_index=True)
    perfil = models.JSONField(default=dict, blank=True)
    resumen = models.TextField(blank=True)
    fortalezas = models.JSONField(default=list, blank=True)
    brechas = models.JSONField(default=list, blank=True)
    resultados_criterios = models.JSONField(default=list, blank=True)
    puntuacion = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, db_index=True)
    modelo = models.CharField(max_length=150)
    version_prompt = models.CharField(max_length=30, default="v1")
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["documento", "rubrica", "numero"], name="analisis_version_unica")]

    def __str__(self):
        return f"{self.documento} - {self.rubrica} - #{self.numero}"
