from decimal import Decimal

from rest_framework import serializers

from .models import EjecucionVacante, EstadoEvaluacion, EstadoTarea, EstadoVacante, EvaluacionVacante, MensajeVacante, RolMensaje, Vacante


class MensajeVacanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MensajeVacante
        fields = ["id", "rol", "contenido", "datos", "created_at"]
        read_only_fields = fields


class VacanteSerializer(serializers.ModelSerializer):
    tarea_activa = serializers.SerializerMethodField()

    class Meta:
        model = Vacante
        fields = ["id", "titulo", "descripcion", "estado", "rubrica", "propuesta", "error", "tarea_activa", "created_at", "updated_at"]
        read_only_fields = fields

    def get_tarea_activa(self, obj):
        return obj.tareas_conversacion.filter(estado__in=[EstadoTarea.PENDIENTE, EstadoTarea.PROCESANDO]).exists()


class CrearVacanteSerializer(serializers.Serializer):
    mensaje = serializers.CharField(trim_whitespace=True, max_length=10000)


class CrearMensajeSerializer(serializers.Serializer):
    contenido = serializers.CharField(trim_whitespace=True, max_length=10000)

    def validate(self, attrs):
        vacante = self.context["vacante"]
        if vacante.estado not in {EstadoVacante.BORRADOR, EstadoVacante.ESPERANDO_CONFIRMACION, EstadoVacante.ERROR}:
            raise serializers.ValidationError("La conversación de esta vacante ya fue confirmada")
        if vacante.tareas_conversacion.filter(estado__in=[EstadoTarea.PENDIENTE, EstadoTarea.PROCESANDO]).exists():
            raise serializers.ValidationError("Espera a que el agente termine de procesar el turno anterior")
        return attrs

    def create(self, validated_data):
        return MensajeVacante.objects.create(
            vacante=self.context["vacante"], rol=RolMensaje.RECLUTADOR, contenido=validated_data["contenido"]
        )


class ConfirmarVacanteSerializer(serializers.Serializer):
    confirmar = serializers.BooleanField(default=True)


class EvaluacionVacanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluacionVacante
        fields = ["id", "documento", "analisis", "estado", "error", "created_at", "started_at", "completed_at"]
        read_only_fields = fields


class EjecucionVacanteSerializer(serializers.ModelSerializer):
    procesando = serializers.SerializerMethodField()
    pendientes = serializers.SerializerMethodField()

    class Meta:
        model = EjecucionVacante
        fields = [
            "id", "numero", "estado", "total", "completados", "procesando", "pendientes", "sin_texto", "errores",
            "error", "created_at", "started_at", "completed_at",
        ]
        read_only_fields = fields

    def get_procesando(self, obj):
        return obj.evaluaciones.filter(estado=EstadoEvaluacion.PROCESANDO).count()

    def get_pendientes(self, obj):
        return obj.evaluaciones.filter(estado=EstadoEvaluacion.PENDIENTE).count()


class RankingSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    puntuacion = serializers.DecimalField(source="analisis.puntuacion", max_digits=5, decimal_places=2, read_only=True)
    resumen = serializers.CharField(source="analisis.resumen", read_only=True)
    fortalezas = serializers.JSONField(source="analisis.fortalezas", read_only=True)
    brechas = serializers.JSONField(source="analisis.brechas", read_only=True)
    criterios = serializers.JSONField(source="analisis.resultados_criterios", read_only=True)
    obligatorios_no_demostrados = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = EvaluacionVacante
        fields = ["id", "documento", "nombre", "puntuacion", "resumen", "fortalezas", "brechas", "criterios", "obligatorios_no_demostrados", "pdf_url"]
        read_only_fields = fields

    def get_nombre(self, obj):
        return obj.analisis.perfil.get("nombre") or obj.documento.remitente or obj.documento.nombre_original

    def get_obligatorios_no_demostrados(self, obj):
        resultados = {item.get("criterio_id"): item for item in obj.analisis.resultados_criterios}
        faltantes = []
        for criterio in obj.ejecucion.vacante.rubrica.criterios.all():
            resultado = resultados.get(criterio.id, {})
            if criterio.obligatorio and (not resultado.get("evidencia") or Decimal(str(resultado.get("puntuacion", 0))) <= 0):
                faltantes.append({"criterio_id": criterio.id, "nombre": criterio.nombre})
        return faltantes

    def get_pdf_url(self, obj):
        ruta = f"/api/documentos/{obj.documento_id}/archivo/"
        request = self.context.get("request")
        return request.build_absolute_uri(ruta) if request else ruta
