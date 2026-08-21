from rest_framework import serializers

from .models import Candidato, EstadoPostulacion, Postulacion


class VacantePublicaSerializer(serializers.Serializer):
    slug = serializers.UUIDField(source="public_slug")
    titulo = serializers.CharField()
    descripcion = serializers.CharField()


class PostulacionPublicaSerializer(serializers.Serializer):
    nombre_completo = serializers.CharField(max_length=200, trim_whitespace=True)
    telefono_whatsapp = serializers.CharField(max_length=50, trim_whitespace=True)
    correo = serializers.EmailField()
    vacante_interes = serializers.CharField(max_length=200, trim_whitespace=True, required=False, allow_blank=True)
    archivo = serializers.FileField()
    consentimiento = serializers.BooleanField()
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)
    turnstile_token = serializers.CharField(required=False, allow_blank=True, write_only=True)


class CurriculumPublicoSerializer(serializers.Serializer):
    archivo = serializers.FileField()
    consentimiento = serializers.BooleanField()
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)
    turnstile_token = serializers.CharField(required=False, allow_blank=True, write_only=True)


class CandidatoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidato
        fields = ["id", "nombre_completo", "telefono_whatsapp", "correo"]


class PostulacionSerializer(serializers.ModelSerializer):
    candidato = CandidatoSerializer(read_only=True)
    vacante_titulo = serializers.SerializerMethodField()
    archivo_nombre = serializers.CharField(source="documento.nombre_original", read_only=True)
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = Postulacion
        fields = ["id", "candidato", "vacante", "vacante_interes", "vacante_titulo", "documento", "archivo_nombre", "archivo_url", "estado", "created_at", "updated_at"]
        read_only_fields = ["id", "candidato", "vacante", "documento", "vacante_titulo", "archivo_nombre", "archivo_url", "created_at", "updated_at"]

    def get_archivo_url(self, obj):
        request = self.context.get("request")
        path = f"/api/postulaciones/{obj.pk}/archivo/"
        return request.build_absolute_uri(path) if request else path

    def get_vacante_titulo(self, obj):
        return obj.vacante.titulo if obj.vacante_id else obj.vacante_interes


class EstadoPostulacionSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=EstadoPostulacion.choices)
