from django.conf import settings
from django.core.checks import Error, register


@register()
def whatsapp_configuration_check(app_configs, **kwargs):
    required = {
        "WHATSAPP_VERIFY_TOKEN": settings.WHATSAPP_VERIFY_TOKEN,
        "WHATSAPP_APP_SECRET": settings.WHATSAPP_APP_SECRET,
        "WHATSAPP_ACCESS_TOKEN": settings.WHATSAPP_ACCESS_TOKEN,
        "WHATSAPP_PHONE_NUMBER_ID": settings.WHATSAPP_PHONE_NUMBER_ID,
        "WHATSAPP_GRAPH_VERSION": settings.WHATSAPP_GRAPH_VERSION,
    }
    missing = [name for name, value in required.items() if not value]
    issues = []
    if not settings.DEBUG:
        if missing:
            issues.append(Error(
                "Falta configuración obligatoria de WhatsApp en producción",
                hint="Defina: " + ", ".join(missing), id="integraciones.E001",
            ))
        if not settings.WHATSAPP_VALIDATE_SIGNATURE:
            issues.append(Error(
                "La validación de firma de WhatsApp no puede desactivarse en producción",
                id="integraciones.E002",
            ))
    return issues
