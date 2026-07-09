from pathlib import Path
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from .exceptions import DocumentoInvalidoError
from .models import Documento
from .serializers import DocumentoSerializer, DocumentoUploadSerializer
from .services import DocumentoRecibido, recibir_documento
class DocumentoListView(generics.ListAPIView):
    queryset = Documento.objects.all(); serializer_class = DocumentoSerializer
    filterset_fields = ["origen", "estado"]; search_fields = ["nombre_original", "remitente", "correo", "telefono"]; ordering_fields = ["fecha_recepcion"]; ordering = ["-fecha_recepcion"]
class DocumentoDetailView(generics.RetrieveAPIView): queryset = Documento.objects.all(); serializer_class = DocumentoSerializer
class DocumentoUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    def post(self, request):
        s = DocumentoUploadSerializer(data=request.data); s.is_valid(raise_exception=True); f = s.validated_data.pop("archivo")
        try: doc, duplicado = recibir_documento(DocumentoRecibido(nombre_original=f.name, contenido=f.read(), mime_type=f.content_type or "", **s.validated_data))
        except DocumentoInvalidoError as exc: return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        body = DocumentoSerializer(doc).data | {"duplicado": duplicado}
        if duplicado: body["message"] = "El documento ya había sido registrado"
        return Response(body, status=status.HTTP_200_OK if duplicado else status.HTTP_201_CREATED)
class DocumentoArchivoView(APIView):
    def get(self, request, pk):
        doc = get_object_or_404(Documento, pk=pk)
        if not doc.archivo or not doc.archivo.storage.exists(doc.archivo.name): raise Http404
        return FileResponse(doc.archivo.open("rb"), content_type="application/pdf", as_attachment=True, filename=Path(doc.nombre_original).name)
