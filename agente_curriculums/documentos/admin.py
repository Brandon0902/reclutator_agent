from pathlib import Path
from django import forms
from django.contrib import admin, messages
from django.http import FileResponse, HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from .exceptions import DocumentoInvalidoError
from .models import Documento, IntentoRecepcionDocumento, OrigenDocumento
from .services import DocumentoRecibido, recibir_documento
from .services.validacion_pdf import validar_pdf
class DocumentoAdminForm(forms.ModelForm):
    class Meta: model = Documento; fields = ["archivo", "remitente", "correo", "telefono", "id_mensaje_origen", "metadata", "estado", "error"]

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        contenido = archivo.read()
        try:
            validar_pdf(archivo.name, contenido, archivo.content_type or "application/octet-stream")
        except DocumentoInvalidoError as exc:
            raise forms.ValidationError(str(exc)) from exc
        finally:
            archivo.seek(0)
        return archivo
@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    form = DocumentoAdminForm
    list_display = ["nombre_original", "origen", "remitente", "correo", "telefono", "estado", "fecha_recepcion", "tamano_bytes", "enlace_descarga"]
    list_filter = ["origen", "estado", "fecha_recepcion"]
    search_fields = ["nombre_original", "remitente", "correo", "telefono", "hash_sha256", "id_mensaje_origen"]
    readonly_fields = ["hash_sha256", "nombre_interno", "tamano_bytes", "fecha_recepcion", "created_at", "updated_at", "enlace_descarga"]
    actions = ["solicitar_analisis"]

    @admin.action(description="Solicitar análisis con la rúbrica predeterminada")
    def solicitar_analisis(self, request, queryset):
        from analisis.services import crear_analisis
        creados = errores = 0
        for documento in queryset:
            try:
                crear_analisis(documento)
                creados += 1
            except Exception as exc:
                errores += 1
                self.message_user(request, f"{documento}: {exc}", level=messages.ERROR)
        self.message_user(request, f"Análisis solicitados: {creados}; errores: {errores}")
    def enlace_descarga(self, obj): return format_html('<a href="{}">Descargar PDF</a>', reverse("admin:documentos_documento_descargar", args=[obj.pk])) if obj.pk else "-"
    enlace_descarga.short_description = "Archivo"
    def get_urls(self): return [path("<int:pk>/descargar/", self.admin_site.admin_view(self.descargar_archivo), name="documentos_documento_descargar")] + super().get_urls()
    def descargar_archivo(self, request, pk):
        obj = self.get_object(request, pk)
        return FileResponse(obj.archivo.open("rb"), as_attachment=True, filename=Path(obj.nombre_original).name, content_type="application/pdf")
    def save_model(self, request, obj, form, change):
        if change: return super().save_model(request, obj, form, change)
        f = form.cleaned_data["archivo"]
        doc, duplicate = recibir_documento(DocumentoRecibido(origen=OrigenDocumento.MANUAL, nombre_original=f.name, contenido=f.read(), mime_type=f.content_type or "application/octet-stream", remitente=form.cleaned_data.get("remitente"), correo=form.cleaned_data.get("correo"), telefono=form.cleaned_data.get("telefono"), id_mensaje_origen=form.cleaned_data.get("id_mensaje_origen"), metadata=form.cleaned_data.get("metadata") or {}))
        obj.pk = doc.pk
        if duplicate:
            request._documento_duplicado = True
            messages.warning(request, "El documento ya había sido registrado")

    def log_addition(self, request, obj, message):
        if not getattr(request, "_documento_duplicado", False):
            super().log_addition(request, obj, message)

    def response_add(self, request, obj, post_url_continue=None):
        if getattr(request, "_documento_duplicado", False):
            return HttpResponseRedirect(reverse("admin:documentos_documento_changelist"))
        return super().response_add(request, obj, post_url_continue)
@admin.register(IntentoRecepcionDocumento)
class IntentoAdmin(admin.ModelAdmin):
    list_display = ["documento", "origen", "remitente", "fecha_recepcion"]
    list_filter = ["origen", "fecha_recepcion"]
    search_fields = ["documento__nombre_original", "correo", "telefono", "id_mensaje_origen"]
    readonly_fields = ["documento", "origen", "id_mensaje_origen", "remitente", "correo", "telefono", "fecha_recepcion", "metadata"]
