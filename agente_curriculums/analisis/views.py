from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from documentos.models import Documento
from .models import AnalisisDocumento, RubricaEvaluacion
from .serializers import AnalisisSerializer, RubricaSerializer
from .services import crear_analisis


class RubricaListCreateView(generics.ListCreateAPIView):
    serializer_class = RubricaSerializer
    filterset_fields = ["activa", "predeterminada"]
    search_fields = ["nombre", "descripcion"]

    def get_queryset(self):
        return RubricaEvaluacion.objects.filter(Q(vacantes__isnull=True) | Q(vacantes__propietario=self.request.user)).prefetch_related("criterios").distinct()


class RubricaDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = RubricaSerializer

    def get_queryset(self):
        return RubricaEvaluacion.objects.filter(Q(vacantes__isnull=True) | Q(vacantes__propietario=self.request.user)).prefetch_related("criterios").distinct()


class AnalisisListView(generics.ListAPIView):
    queryset = AnalisisDocumento.objects.select_related("documento", "rubrica")
    serializer_class = AnalisisSerializer
    filterset_fields = ["rubrica", "estado", "documento"]
    ordering_fields = ["puntuacion", "created_at", "completed_at"]
    ordering = ["-puntuacion", "-created_at"]
    search_fields = ["documento__nombre_original", "documento__correo", "resumen"]


class AnalisisDetailView(generics.RetrieveAPIView):
    queryset = AnalisisDocumento.objects.select_related("documento", "rubrica")
    serializer_class = AnalisisSerializer


class DocumentoAnalisisListView(generics.ListAPIView):
    serializer_class = AnalisisSerializer

    def get_queryset(self):
        return AnalisisDocumento.objects.filter(documento_id=self.kwargs["pk"]).select_related("documento", "rubrica")


class SolicitarAnalisisView(APIView):
    def post(self, request, pk):
        documento = get_object_or_404(Documento, pk=pk)
        rubrica = None
        if request.data.get("rubrica"):
            rubrica = get_object_or_404(RubricaEvaluacion, pk=request.data["rubrica"], activa=True)
        try:
            analisis = crear_analisis(documento, rubrica)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AnalisisSerializer(analisis).data, status=status.HTTP_201_CREATED)
