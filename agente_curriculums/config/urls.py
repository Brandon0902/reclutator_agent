from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

class HealthView(APIView):
    permission_classes = [AllowAny]
    def get(self, request): return Response({"status": "ok"})

urlpatterns = [
    path("", include("vacantes.web_urls")),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view()),
    path("api/documentos/", include("documentos.urls")),
    path("api/", include("analisis.urls")),
    path("api/vacantes/", include("vacantes.urls")),
    path("api/webhooks/", include("integraciones.urls")),
    path("api-auth/", include("rest_framework.urls")),
]
