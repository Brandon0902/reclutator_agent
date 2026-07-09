from django.urls import path

from .views import ConfirmarVacanteView, EjecucionDetailView, EjecucionListView, IniciarEvaluacionView, MensajeListCreateView, RankingView, ReintentarEjecucionView, VacanteDetailView, VacanteListCreateView


urlpatterns = [
    path("", VacanteListCreateView.as_view()),
    path("<int:pk>/", VacanteDetailView.as_view()),
    path("<int:pk>/mensajes/", MensajeListCreateView.as_view()),
    path("<int:pk>/confirmar/", ConfirmarVacanteView.as_view()),
    path("<int:pk>/evaluar/", IniciarEvaluacionView.as_view()),
    path("<int:pk>/ejecuciones/", EjecucionListView.as_view()),
    path("<int:pk>/ejecuciones/<int:ejecucion_id>/", EjecucionDetailView.as_view()),
    path("<int:pk>/ejecuciones/<int:ejecucion_id>/ranking/", RankingView.as_view()),
    path("<int:pk>/ejecuciones/<int:ejecucion_id>/reintentar/", ReintentarEjecucionView.as_view()),
]
