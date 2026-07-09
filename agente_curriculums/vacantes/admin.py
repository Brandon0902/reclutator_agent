from django.contrib import admin

from .models import EjecucionVacante, EvaluacionVacante, MensajeVacante, TareaConversacion, Vacante


@admin.register(Vacante)
class VacanteAdmin(admin.ModelAdmin):
    list_display = ["titulo", "propietario", "estado", "rubrica", "created_at"]
    list_filter = ["estado"]
    search_fields = ["titulo", "descripcion", "propietario__username"]


@admin.register(MensajeVacante)
class MensajeVacanteAdmin(admin.ModelAdmin):
    list_display = ["vacante", "rol", "created_at"]
    list_filter = ["rol"]


@admin.register(TareaConversacion)
class TareaConversacionAdmin(admin.ModelAdmin):
    list_display = ["vacante", "estado", "intentos", "created_at", "completed_at"]
    list_filter = ["estado"]


@admin.register(EjecucionVacante)
class EjecucionVacanteAdmin(admin.ModelAdmin):
    list_display = ["vacante", "numero", "estado", "total", "completados", "errores", "created_at"]
    list_filter = ["estado"]


@admin.register(EvaluacionVacante)
class EvaluacionVacanteAdmin(admin.ModelAdmin):
    list_display = ["ejecucion", "documento", "estado", "analisis", "completed_at"]
    list_filter = ["estado"]
