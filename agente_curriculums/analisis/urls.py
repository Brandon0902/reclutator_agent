from django.urls import path

from .views import (
    AnalisisDetailView, AnalisisListView, DocumentoAnalisisListView, RubricaDetailView,
    RubricaListCreateView, SolicitarAnalisisView,
)


urlpatterns = [
    path("rubricas/", RubricaListCreateView.as_view()),
    path("rubricas/<int:pk>/", RubricaDetailView.as_view()),
    path("analisis/", AnalisisListView.as_view()),
    path("analisis/<int:pk>/", AnalisisDetailView.as_view()),
    path("documentos/<int:pk>/analisis/", DocumentoAnalisisListView.as_view()),
    path("documentos/<int:pk>/analizar/", SolicitarAnalisisView.as_view()),
]
