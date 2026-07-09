import requests, msal
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
class MicrosoftGraphClient:
    def __init__(self):
        required = [settings.MICROSOFT_TENANT_ID, settings.MICROSOFT_CLIENT_ID, settings.MICROSOFT_CLIENT_SECRET, settings.MICROSOFT_MAILBOX]
        if not all(required): raise ImproperlyConfigured("Faltan credenciales de Microsoft Graph")
        self.base = "https://graph.microsoft.com/v1.0"; self.mailbox = settings.MICROSOFT_MAILBOX
        self.app = msal.ConfidentialClientApplication(settings.MICROSOFT_CLIENT_ID, authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}", client_credential=settings.MICROSOFT_CLIENT_SECRET)
    def obtener_token(self):
        result = self.app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in result: raise RuntimeError(result.get("error_description", "No fue posible obtener token"))
        return result["access_token"]
    def _get(self, url):
        response = requests.get(url, headers={"Authorization": f"Bearer {self.obtener_token()}"}, timeout=30); response.raise_for_status(); return response
    def obtener_mensajes_con_adjuntos(self): return self._get(f"{self.base}/users/{self.mailbox}/messages?$filter=hasAttachments eq true&$select=id,subject,from,receivedDateTime").json().get("value", [])
    def obtener_adjuntos(self, message_id): return self._get(f"{self.base}/users/{self.mailbox}/messages/{message_id}/attachments").json().get("value", [])
    def descargar_adjunto(self, message_id, attachment_id): return self._get(f"{self.base}/users/{self.mailbox}/messages/{message_id}/attachments/{attachment_id}/$value").content
