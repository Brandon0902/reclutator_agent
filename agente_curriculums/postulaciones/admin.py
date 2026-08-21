from django.contrib import admin

from .models import Candidato, Postulacion


@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ["nombre_completo", "correo", "telefono_whatsapp", "created_at"]
    search_fields = ["nombre_completo", "correo", "telefono_whatsapp"]


@admin.register(Postulacion)
class PostulacionAdmin(admin.ModelAdmin):
    list_display = ["candidato", "vacante", "estado", "created_at"]
    list_filter = ["estado", "vacante", "created_at"]
    search_fields = ["candidato__nombre_completo", "candidato__correo", "candidato__telefono_whatsapp"]
    readonly_fields = ["consentimiento_at", "consentimiento_version", "ip_hash", "user_agent_reducido", "created_at", "updated_at"]
