from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from .models import AnalisisDocumento, CriterioEvaluacion, RubricaEvaluacion


class CriterioSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriterioEvaluacion
        fields = ["id", "nombre", "descripcion", "peso", "obligatorio", "orden"]
        read_only_fields = ["id"]


class RubricaSerializer(serializers.ModelSerializer):
    criterios = CriterioSerializer(many=True)

    class Meta:
        model = RubricaEvaluacion
        fields = ["id", "nombre", "descripcion", "version", "activa", "predeterminada", "criterios", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_criterios(self, criterios):
        total = sum((item["peso"] for item in criterios), Decimal("0"))
        if total != Decimal("100"):
            raise serializers.ValidationError(f"Los pesos deben sumar 100; suma actual: {total}")
        return criterios

    @transaction.atomic
    def create(self, validated_data):
        criterios = validated_data.pop("criterios")
        rubrica = RubricaEvaluacion.objects.create(**validated_data)
        CriterioEvaluacion.objects.bulk_create([CriterioEvaluacion(rubrica=rubrica, **item) for item in criterios])
        return rubrica

    @transaction.atomic
    def update(self, instance, validated_data):
        if instance.analisis.exists() or instance.vacantes.exists():
            raise serializers.ValidationError("Una rúbrica utilizada es inmutable; cree una versión nueva")
        criterios = validated_data.pop("criterios", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if criterios is not None:
            instance.criterios.all().delete()
            CriterioEvaluacion.objects.bulk_create([CriterioEvaluacion(rubrica=instance, **item) for item in criterios])
        return instance


class AnalisisSerializer(serializers.ModelSerializer):
    documento_nombre = serializers.CharField(source="documento.nombre_original", read_only=True)
    rubrica_nombre = serializers.SerializerMethodField()

    def get_rubrica_nombre(self, obj):
        return str(obj.rubrica)

    class Meta:
        model = AnalisisDocumento
        fields = [
            "id", "documento", "documento_nombre", "rubrica", "rubrica_nombre", "numero", "estado", "perfil",
            "resumen", "fortalezas", "brechas", "resultados_criterios", "puntuacion", "modelo", "version_prompt",
            "error", "created_at", "started_at", "completed_at",
        ]
        read_only_fields = fields
