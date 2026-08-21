from django.urls import path

from .views import formulario_publico, formulario_publico_general, postulaciones_panel


urlpatterns = [
    path("aplicar/", formulario_publico_general, name="formulario-aplicar-general"),
    path("aplicar/<uuid:slug>/", formulario_publico, name="formulario-aplicar"),
    path("postulaciones/", postulaciones_panel, name="postulaciones-panel"),
]
