from django.urls import path
from .views import DocumentoArchivoView, DocumentoDetailView, DocumentoListView, DocumentoUploadView
urlpatterns = [path("", DocumentoListView.as_view()), path("upload/", DocumentoUploadView.as_view()), path("<int:pk>/", DocumentoDetailView.as_view()), path("<int:pk>/archivo/", DocumentoArchivoView.as_view())]
