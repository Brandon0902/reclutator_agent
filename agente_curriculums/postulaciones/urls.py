from django.urls import path

from .views import PostulacionArchivoView, PostulacionDetailView, PostulacionListView, PublicCurriculumCreateView, PublicPostulacionCreateView, PublicVacanteView


urlpatterns = [
    path("public/curriculums/", PublicCurriculumCreateView.as_view()),
    path("public/postulaciones/", PublicPostulacionCreateView.as_view()),
    path("public/vacantes/<uuid:slug>/", PublicVacanteView.as_view()),
    path("public/vacantes/<uuid:slug>/postulaciones/", PublicPostulacionCreateView.as_view()),
    path("", PostulacionListView.as_view()),
    path("<int:pk>/", PostulacionDetailView.as_view()),
    path("<int:pk>/archivo/", PostulacionArchivoView.as_view()),
]
