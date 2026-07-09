import hashlib
import hmac

from django.conf import settings


def firma_valida(body: bytes, signature: str) -> bool:
    if not settings.WHATSAPP_VALIDATE_SIGNATURE:
        return bool(settings.DEBUG)
    if not settings.WHATSAPP_APP_SECRET or not signature.startswith("sha256="):
        return False
    esperada = "sha256=" + hmac.new(settings.WHATSAPP_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, signature)
