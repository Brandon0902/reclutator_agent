from decimal import Decimal

from django import forms
from django.contrib import admin, messages
from django.forms.models import BaseInlineFormSet

from .models import AnalisisDocumento, ContenidoExtraido, CriterioEvaluacion, RubricaEvaluacion
from .services import crear_analisis


class CriterioInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        total = sum(
            (form.cleaned_data.get("peso") or Decimal("0"))
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        )
        if total != Decimal("100"):
            raise forms.ValidationError(f"Los pesos deben sumar 100; suma actual: {total}")


class CriterioInline(admin.TabularInline):
    model = CriterioEvaluacion
    formset = CriterioInlineFormSet
    extra = 1

    def has_add_permission(self, request, obj=None):
        return not obj or not obj.analisis.exists()

    def has_change_permission(self, request, obj=None):
        return not obj or not obj.analisis.exists()

    def has_delete_permission(self, request, obj=None):
        return not obj or not obj.analisis.exists()


@admin.register(RubricaEvaluacion)
class RubricaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "version", "activa", "predeterminada", "created_at"]
    list_filter = ["activa", "predeterminada"]
    search_fields = ["nombre", "descripcion"]
    inlines = [CriterioInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.analisis.exists():
            return ["nombre", "descripcion", "version", "activa", "predeterminada", "created_at"]
        return ["created_at"]


@admin.register(ContenidoExtraido)
class ContenidoExtraidoAdmin(admin.ModelAdmin):
    list_display = ["documento", "estado", "paginas", "caracteres", "extracted_at"]
    list_filter = ["estado", "extracted_at"]
    search_fields = ["documento__nombre_original", "texto"]
    readonly_fields = ["documento", "texto", "paginas", "caracteres", "version_extractor", "estado", "error", "extracted_at"]

    def has_add_permission(self, request):
        return False


@admin.register(AnalisisDocumento)
class AnalisisDocumentoAdmin(admin.ModelAdmin):
    list_display = ["documento", "rubrica", "numero", "estado", "puntuacion", "modelo", "created_at"]
    list_filter = ["estado", "rubrica", "modelo", "created_at"]
    search_fields = ["documento__nombre_original", "documento__correo", "resumen"]
    ordering = ["-puntuacion", "-created_at"]
    readonly_fields = [
        "documento", "rubrica", "numero", "estado", "perfil", "resumen", "fortalezas", "brechas",
        "resultados_criterios", "puntuacion", "modelo", "version_prompt", "error", "created_at", "started_at", "completed_at",
    ]

    def has_add_permission(self, request):
        return False


def solicitar_reanalisis(modeladmin, request, queryset):
    creados = errores = 0
    for documento in queryset:
        try:
            crear_analisis(documento)
            creados += 1
        except Exception as exc:
            errores += 1
            modeladmin.message_user(request, f"{documento}: {exc}", level=messages.ERROR)
    modeladmin.message_user(request, f"Análisis solicitados: {creados}; errores: {errores}")


solicitar_reanalisis.short_description = "Solicitar análisis con la rúbrica predeterminada"
