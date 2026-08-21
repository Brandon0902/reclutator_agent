from django.contrib import admin

from .models import EventoWebhook, MensajeExternoProcesado, MensajeWhatsApp


@admin.register(MensajeExternoProcesado)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ["origen", "id_mensaje", "estado", "fecha_procesamiento"]
    list_filter = ["origen", "estado"]
    search_fields = ["id_mensaje"]
    readonly_fields = ["origen", "id_mensaje", "fecha_procesamiento", "estado", "error", "metadata"]


@admin.register(EventoWebhook)
class EventoWebhookAdmin(admin.ModelAdmin):
    list_display = ["id", "proveedor", "objeto", "estado", "recibido_at", "procesado_at"]
    list_filter = ["proveedor", "estado"]
    search_fields = ["payload_sha256"]
    readonly_fields = [
        "proveedor", "payload_sha256", "objeto", "estado", "payload_sanitizado",
        "intentos", "error", "recibido_at", "procesado_at",
    ]


@admin.register(MensajeWhatsApp)
class MensajeWhatsAppAdmin(admin.ModelAdmin):
    list_display = ["wamid", "tipo", "direccion", "wa_id_enmascarado", "estado", "recibido_at"]
    list_filter = ["tipo", "direccion", "estado"]
    search_fields = ["wamid", "nombre_archivo"]
    readonly_fields = [
        "evento", "wamid", "direccion", "tipo", "wa_id", "nombre_perfil", "contenido_texto",
        "media_id", "nombre_archivo", "mime_type", "documento", "timestamp_meta", "estado", "error",
        "recibido_at", "procesado_at",
    ]

    @admin.display(description="Contacto")
    def wa_id_enmascarado(self, obj):
        return f"***{obj.wa_id[-4:]}" if obj.wa_id else ""
