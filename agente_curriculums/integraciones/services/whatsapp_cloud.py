import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
class WhatsAppCloudClient:
    def __init__(self):
        if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_API_VERSION: raise ImproperlyConfigured("Faltan token o versión activa de WhatsApp")
        self.headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}; self.base = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
    def obtener_media_url(self, media_id):
        r = requests.get(f"{self.base}/{media_id}", headers=self.headers, timeout=30); r.raise_for_status(); url = r.json().get("url")
        if not url: raise RuntimeError("Meta no devolvió URL para el archivo")
        return url
    def descargar_media(self, media_url):
        r = requests.get(media_url, headers=self.headers, timeout=30); r.raise_for_status(); return r.content, r.headers.get("Content-Type", "")
