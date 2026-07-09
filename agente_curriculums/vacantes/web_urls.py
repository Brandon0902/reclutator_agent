from django.urls import path

from .web_views import workspace


urlpatterns = [path("", workspace, name="workspace")]
