from rest_framework import serializers
from .models import Documento, OrigenDocumento
class DocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documento
        fields = ["id", "nombre_original", "origen", "id_mensaje_origen", "remitente", "correo", "telefono", "mime_type", "tamano_bytes", "estado", "fecha_recepcion", "metadata"]
        read_only_fields = fields
class DocumentoUploadSerializer(serializers.Serializer):
    archivo = serializers.FileField()
    origen = serializers.ChoiceField(choices=OrigenDocumento.choices, default=OrigenDocumento.MANUAL)
    remitente = serializers.CharField(required=False, allow_blank=True); correo = serializers.EmailField(required=False, allow_blank=True); telefono = serializers.CharField(required=False, allow_blank=True); id_mensaje_origen = serializers.CharField(required=False, allow_blank=True)
