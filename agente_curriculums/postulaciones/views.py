from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from vacantes.models import Vacante

from .models import EstadoPostulacion, Postulacion
from .permissions import EsRH, es_rh, limitar_postulaciones, puede_cambiar
from .serializers import CurriculumPublicoSerializer, EstadoPostulacionSerializer, PostulacionPublicaSerializer, PostulacionSerializer, VacantePublicaSerializer
from .services import PostulacionInvalida, recibir_curriculum_publico, recibir_postulacion


class PublicVacanteView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        vacante = get_object_or_404(Vacante, public_slug=slug, publicada=True)
        if vacante.fecha_cierre and vacante.fecha_cierre <= timezone.now():
            return Response({"detail": "Esta vacante ya no está disponible."}, status=status.HTTP_410_GONE)
        return Response(VacantePublicaSerializer(vacante).data)


class PublicPostulacionCreateView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug=None):
        vacante = get_object_or_404(Vacante, public_slug=slug, publicada=True) if slug else None
        serializer = PostulacionPublicaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            data = serializer.validated_data
            postulacion = recibir_postulacion(
                vacante=vacante,
                request=request,
                nombre=data["nombre_completo"],
                telefono=data["telefono_whatsapp"],
                correo=data["correo"],
                archivo=data["archivo"],
                consentimiento=data["consentimiento"],
                vacante_interes=data.get("vacante_interes", ""),
            )
        except PostulacionInvalida as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": postulacion.pk, "message": "Tu postulación fue recibida correctamente."}, status=status.HTTP_201_CREATED)


class PublicCurriculumCreateView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = CurriculumPublicoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            _, duplicado = recibir_curriculum_publico(
                archivo=serializer.validated_data["archivo"],
                consentimiento=serializer.validated_data["consentimiento"],
                request=request,
            )
        except PostulacionInvalida as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        message = "Este currículum ya estaba guardado." if duplicado else "Tu currículum fue guardado correctamente."
        return Response(
            {"message": message, "duplicado": duplicado},
            status=status.HTTP_200_OK if duplicado else status.HTTP_201_CREATED,
        )


class PostulacionListView(generics.ListAPIView):
    permission_classes = [EsRH]
    serializer_class = PostulacionSerializer
    filterset_fields = ["vacante", "estado"]
    search_fields = ["candidato__nombre_completo", "candidato__correo", "candidato__telefono_whatsapp", "vacante_interes"]
    ordering_fields = ["created_at", "updated_at", "estado"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Postulacion.objects.select_related("candidato", "vacante", "documento")
        return limitar_postulaciones(queryset, self.request.user)


class PostulacionDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [EsRH]
    serializer_class = PostulacionSerializer

    def get_queryset(self):
        queryset = Postulacion.objects.select_related("candidato", "vacante", "documento")
        return limitar_postulaciones(queryset, self.request.user)

    def update(self, request, *args, **kwargs):
        if not puede_cambiar(request.user):
            return Response({"detail": "No tienes permiso para cambiar estados."}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        serializer = EstadoPostulacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance.estado = serializer.validated_data["estado"]
        instance.save(update_fields=["estado", "updated_at"])
        return Response(PostulacionSerializer(instance, context={"request": request}).data)


class PostulacionArchivoView(APIView):
    permission_classes = [EsRH]

    def get(self, request, pk):
        queryset = limitar_postulaciones(Postulacion.objects.select_related("documento", "vacante"), request.user)
        postulacion = get_object_or_404(queryset, pk=pk)
        archivo = postulacion.documento.archivo
        if not archivo or not archivo.storage.exists(archivo.name):
            raise Http404
        return FileResponse(archivo.open("rb"), content_type="application/pdf", as_attachment=True, filename=Path(postulacion.documento.nombre_original).name)


@login_required
def postulaciones_panel(request):
    if not es_rh(request.user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request, "postulaciones/panel.html")


def formulario_publico(request, slug):
    vacante = get_object_or_404(Vacante, public_slug=slug, publicada=True)
    cerrada = bool(vacante.fecha_cierre and vacante.fecha_cierre <= timezone.now())
    return render(request, "postulaciones/aplicar.html", {
        "vacante": vacante,
        "cerrada": cerrada,
        "max_pdf_mb": settings.PUBLIC_FORM_MAX_PDF_SIZE_MB,
        "turnstile_enabled": settings.TURNSTILE_ENABLED,
        "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
        "postulacion_api_url": f"/api/postulaciones/public/vacantes/{vacante.public_slug}/postulaciones/",
    })


def formulario_publico_general(request):
    return render(request, "postulaciones/aplicar.html", {
        "vacante": None,
        "modo_curriculum": True,
        "cerrada": False,
        "max_pdf_mb": settings.PUBLIC_FORM_MAX_PDF_SIZE_MB,
        "turnstile_enabled": settings.TURNSTILE_ENABLED,
        "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
        "privacy_notice_url": settings.PRIVACY_NOTICE_URL,
        "postulacion_api_url": "/api/postulaciones/public/curriculums/",
    })
