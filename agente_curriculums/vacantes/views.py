from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EjecucionVacante, EstadoEvaluacion, EvaluacionVacante, MensajeVacante, RolMensaje, TareaConversacion, Vacante
from .serializers import ConfirmarVacanteSerializer, CrearMensajeSerializer, CrearVacanteSerializer, EjecucionVacanteSerializer, MensajeVacanteSerializer, RankingSerializer, VacanteSerializer
from .services import confirmar_vacante, crear_ejecucion, reintentar_errores


class VacanteListCreateView(generics.ListAPIView):
    serializer_class = VacanteSerializer

    def get_queryset(self):
        return Vacante.objects.filter(propietario=self.request.user).select_related("rubrica")

    @transaction.atomic
    def post(self, request):
        serializer = CrearVacanteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mensaje = serializer.validated_data["mensaje"]
        vacante = Vacante.objects.create(propietario=request.user, descripcion=mensaje)
        mensaje_obj = MensajeVacante.objects.create(vacante=vacante, rol=RolMensaje.RECLUTADOR, contenido=mensaje)
        TareaConversacion.objects.create(vacante=vacante, mensaje=mensaje_obj)
        return Response(VacanteSerializer(vacante).data, status=status.HTTP_202_ACCEPTED)


class VacanteDetailView(generics.RetrieveAPIView):
    serializer_class = VacanteSerializer

    def get_queryset(self):
        return Vacante.objects.filter(propietario=self.request.user).select_related("rubrica")


class MensajeListCreateView(APIView):
    def _vacante(self, request, pk):
        return get_object_or_404(Vacante, pk=pk, propietario=request.user)

    def get(self, request, pk):
        vacante = self._vacante(request, pk)
        return Response(MensajeVacanteSerializer(vacante.mensajes.all(), many=True).data)

    def post(self, request, pk):
        vacante = self._vacante(request, pk)
        serializer = CrearMensajeSerializer(data=request.data, context={"vacante": vacante})
        serializer.is_valid(raise_exception=True)
        mensaje = serializer.save()
        TareaConversacion.objects.create(vacante=vacante, mensaje=mensaje)
        return Response(MensajeVacanteSerializer(mensaje).data, status=status.HTTP_202_ACCEPTED)


class ConfirmarVacanteView(APIView):
    def post(self, request, pk):
        vacante = get_object_or_404(Vacante, pk=pk, propietario=request.user)
        serializer = ConfirmarVacanteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirmar_vacante(vacante)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(VacanteSerializer(vacante).data)


class IniciarEvaluacionView(APIView):
    def post(self, request, pk):
        vacante = get_object_or_404(Vacante, pk=pk, propietario=request.user)
        try:
            ejecucion = crear_ejecucion(vacante)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EjecucionVacanteSerializer(ejecucion).data, status=status.HTTP_202_ACCEPTED)


class EjecucionListView(generics.ListAPIView):
    serializer_class = EjecucionVacanteSerializer

    def get_queryset(self):
        return EjecucionVacante.objects.filter(vacante_id=self.kwargs["pk"], vacante__propietario=self.request.user)


class EjecucionDetailView(generics.RetrieveAPIView):
    serializer_class = EjecucionVacanteSerializer
    lookup_url_kwarg = "ejecucion_id"

    def get_queryset(self):
        return EjecucionVacante.objects.filter(vacante_id=self.kwargs["pk"], vacante__propietario=self.request.user)


class RankingPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class RankingView(generics.ListAPIView):
    serializer_class = RankingSerializer
    pagination_class = RankingPagination

    def get_queryset(self):
        return EvaluacionVacante.objects.filter(
            ejecucion_id=self.kwargs["ejecucion_id"], ejecucion__vacante_id=self.kwargs["pk"],
            ejecucion__vacante__propietario=self.request.user, estado=EstadoEvaluacion.COMPLETADA,
        ).select_related("documento", "analisis", "ejecucion__vacante__rubrica").prefetch_related("ejecucion__vacante__rubrica__criterios").order_by("-analisis__puntuacion", "documento_id")


class ReintentarEjecucionView(APIView):
    def post(self, request, pk, ejecucion_id):
        ejecucion = get_object_or_404(EjecucionVacante, pk=ejecucion_id, vacante_id=pk, vacante__propietario=request.user)
        try:
            ejecucion = reintentar_errores(ejecucion)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EjecucionVacanteSerializer(ejecucion).data, status=status.HTTP_202_ACCEPTED)
