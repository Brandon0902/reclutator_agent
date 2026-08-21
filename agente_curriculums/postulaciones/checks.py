from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def public_form_security_checks(app_configs, **kwargs):
    issues = []
    if settings.TURNSTILE_ENABLED and (not settings.TURNSTILE_SITE_KEY or not settings.TURNSTILE_SECRET_KEY):
        issues.append(Error(
            "Turnstile está habilitado pero faltan sus claves.",
            hint="Configure TURNSTILE_SITE_KEY y TURNSTILE_SECRET_KEY.",
            id="postulaciones.E001",
        ))
    if not settings.PDF_ANTIVIRUS_ENABLED:
        issues.append(Warning(
            "El análisis antivirus de PDFs está deshabilitado.",
            hint="Habilite PDF_ANTIVIRUS_ENABLED y configure CLAMAV_HOST para producción.",
            id="postulaciones.W001",
        ))
    if settings.PUBLIC_FORM_RATE_LIMIT < 1 or settings.PUBLIC_FORM_IP_RATE_LIMIT < 1:
        issues.append(Error(
            "Los límites del formulario público deben ser mayores que cero.",
            id="postulaciones.E002",
        ))
    return issues
