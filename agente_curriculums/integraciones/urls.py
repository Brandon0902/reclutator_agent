from django.urls import path
from .views.whatsapp import whatsapp_webhook
urlpatterns = [path("whatsapp/", whatsapp_webhook, name="whatsapp-webhook")]
