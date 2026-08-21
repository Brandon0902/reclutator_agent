import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class MediaWhatsAppDemasiadoGrande(ValueError):
    pass


class WhatsAppCloudClient:
    def __init__(self):
        if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_API_VERSION: raise ImproperlyConfigured("Faltan token o versión activa de WhatsApp")
        self.headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}; self.base = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
    def obtener_media_url(self, media_id):
        r = requests.get(f"{self.base}/{media_id}", headers=self.headers, timeout=30); r.raise_for_status(); url = r.json().get("url")
        if not url: raise RuntimeError("Meta no devolvió URL para el archivo")
        return url
    def descargar_media(self, media_url, max_bytes=None):
        limite = max_bytes or settings.WHATSAPP_MAX_DOCUMENT_SIZE_MB * 1024 * 1024
        with requests.get(media_url, headers=self.headers, timeout=30, stream=True) as respuesta:
            respuesta.raise_for_status()
            longitud = respuesta.headers.get("Content-Length")
            if longitud and int(longitud) > limite:
                raise MediaWhatsAppDemasiadoGrande("El documento supera el tamaño máximo permitido")
            partes = []
            total = 0
            for parte in respuesta.iter_content(chunk_size=64 * 1024):
                if not parte:
                    continue
                total += len(parte)
                if total > limite:
                    raise MediaWhatsAppDemasiadoGrande("El documento supera el tamaño máximo permitido")
                partes.append(parte)
            return b"".join(partes), respuesta.headers.get("Content-Type", "").split(";", 1)[0].strip()
