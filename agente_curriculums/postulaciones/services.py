import socket
from datetime import timedelta
from io import BytesIO

import fitz
import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from documentos.exceptions import DocumentoInvalidoError
from documentos.models import OrigenDocumento
from documentos.services import DocumentoRecibido, recibir_documento
from documentos.services.almacenamiento import eliminar_archivo

from .models import Candidato, IntentoPostulacionPublica, Postulacion, hash_identifier, hash_ip


class PostulacionInvalida(Exception):
    pass


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",", 1)[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")


def _check_rate_limit(request, vacante=None, correo="", telefono=""):
    since = timezone.now() - timedelta(seconds=settings.PUBLIC_FORM_RATE_WINDOW_SECONDS)
    ip_hash = hash_ip(_client_ip(request))
    correo_hash = hash_identifier(correo, "correo")
    telefono_hash = hash_identifier(telefono, "telefono")
    attempts = IntentoPostulacionPublica.objects.filter(created_at__gte=since)
    if ip_hash and attempts.filter(ip_hash=ip_hash).count() >= settings.PUBLIC_FORM_IP_RATE_LIMIT:
        raise PostulacionInvalida("Se alcanzó el límite temporal de envíos. Intenta más tarde.")
    identity_filter = Q()
    if correo_hash:
        identity_filter |= Q(correo_hash=correo_hash)
    if telefono_hash:
        identity_filter |= Q(telefono_hash=telefono_hash)
    if identity_filter and attempts.filter(identity_filter).count() >= settings.PUBLIC_FORM_RATE_LIMIT:
        raise PostulacionInvalida("Se alcanzó el límite temporal de envíos. Intenta más tarde.")
    IntentoPostulacionPublica.objects.create(
        vacante=vacante, ip_hash=ip_hash, correo_hash=correo_hash, telefono_hash=telefono_hash
    )


def _verify_turnstile(request):
    if not settings.TURNSTILE_ENABLED:
        return
    token = request.data.get("turnstile_token", "")
    if not token or not settings.TURNSTILE_SECRET_KEY:
        raise PostulacionInvalida("No se pudo validar la protección anti-spam.")
    try:
        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": settings.TURNSTILE_SECRET_KEY, "response": token, "remoteip": _client_ip(request)},
            timeout=5,
        )
        if not response.ok or not response.json().get("success"):
            raise PostulacionInvalida("No se pudo validar la protección anti-spam.")
    except (requests.RequestException, ValueError) as exc:
        raise PostulacionInvalida("No se pudo validar la protección anti-spam.") from exc


def _scan_antivirus(content):
    if not settings.PDF_ANTIVIRUS_ENABLED:
        return
    try:
        with socket.create_connection((settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=5) as client:
            client.sendall(b"zINSTREAM\0")
            stream = BytesIO(content)
            while chunk := stream.read(1024 * 1024):
                client.sendall(len(chunk).to_bytes(4, "big") + chunk)
            client.sendall((0).to_bytes(4, "big"))
            result = client.recv(4096).decode("utf-8", "replace")
        if "OK" not in result or "FOUND" in result:
            raise PostulacionInvalida("El archivo no pasó el análisis de seguridad.")
    except (OSError, TimeoutError) as exc:
        raise PostulacionInvalida("El análisis de seguridad no está disponible.") from exc


def _validate_pdf_structure(content):
    try:
        with fitz.open(stream=content, filetype="pdf") as pdf:
            if pdf.page_count > 50:
                raise PostulacionInvalida("El PDF supera el máximo de 50 páginas.")
    except PostulacionInvalida:
        raise
    except Exception as exc:
        raise PostulacionInvalida("El PDF está dañado o no puede ser leído.") from exc


def recibir_curriculum_publico(*, archivo, consentimiento, request):
    """Guarda un PDF en el banco general sin crear candidato ni postulación."""
    if not consentimiento:
        raise PostulacionInvalida("Debes aceptar el tratamiento de los datos contenidos en tu currículum.")
    if request.data.get("website", ""):
        raise PostulacionInvalida("No se pudo procesar la solicitud.")

    _verify_turnstile(request)
    _check_rate_limit(request)
    content = archivo.read()
    if len(content) > settings.PUBLIC_FORM_MAX_PDF_SIZE_MB * 1024 * 1024:
        raise PostulacionInvalida("El archivo supera el tamaño máximo permitido.")
    _validate_pdf_structure(content)
    _scan_antivirus(content)
    try:
        return recibir_documento(DocumentoRecibido(
            origen=OrigenDocumento.FORMULARIO_WEB,
            nombre_original=archivo.name,
            contenido=content,
            mime_type=archivo.content_type or "",
            metadata={
                "consentimiento_datos": True,
                "consentimiento_version": "curriculum-v1",
                "consentimiento_at": timezone.now().isoformat(),
                "ip_hash": hash_ip(_client_ip(request)),
                "user_agent_reducido": request.META.get("HTTP_USER_AGENT", "")[:255],
            },
        ))
    except DocumentoInvalidoError as exc:
        raise PostulacionInvalida(str(exc)) from exc


def recibir_postulacion(*, nombre, telefono, correo, archivo, consentimiento, request, vacante=None, vacante_interes=""):
    if vacante and (not vacante.publicada or (vacante.fecha_cierre and vacante.fecha_cierre <= timezone.now())):
        raise PostulacionInvalida("Esta vacante ya no está disponible.")
    if not consentimiento:
        raise PostulacionInvalida("Debes aceptar el consentimiento para el tratamiento de datos.")
    if request.data.get("website", ""):
        raise PostulacionInvalida("No se pudo procesar la solicitud.")

    correo = correo.strip().lower()
    telefono = telefono.strip()
    vacante_interes = (vacante.titulo if vacante else vacante_interes).strip()
    if not vacante_interes:
        raise PostulacionInvalida("Indica la vacante a la que deseas aplicar.")
    _verify_turnstile(request)
    _check_rate_limit(request, vacante, correo, telefono)
    content = archivo.read()
    if len(content) > settings.PUBLIC_FORM_MAX_PDF_SIZE_MB * 1024 * 1024:
        raise PostulacionInvalida("El archivo supera el tamaño máximo permitido.")
    _validate_pdf_structure(content)
    _scan_antivirus(content)
    documento = None
    documento_creado = False
    try:
        with transaction.atomic():
            documento, duplicado = recibir_documento(DocumentoRecibido(
                origen=OrigenDocumento.FORMULARIO_WEB,
                nombre_original=archivo.name,
                contenido=content,
                mime_type=archivo.content_type or "",
                remitente=nombre.strip(),
                correo=correo,
                telefono=telefono,
            ))
            documento_creado = not duplicado
            candidato = Candidato.objects.create(
                nombre_completo=nombre.strip(), telefono_whatsapp=telefono, correo=correo
            )
            if Postulacion.objects.filter(vacante=vacante, documento=documento).exists():
                raise IntegrityError("postulación duplicada")
            postulacion = Postulacion.objects.create(
                candidato=candidato,
                vacante=vacante,
                vacante_interes=vacante_interes,
                documento=documento,
                consentimiento_datos=True,
                consentimiento_version="v1",
                ip_hash=hash_ip(_client_ip(request)),
                user_agent_reducido=request.META.get("HTTP_USER_AGENT", "")[:255],
            )
    except DocumentoInvalidoError as exc:
        raise PostulacionInvalida(str(exc)) from exc
    except IntegrityError as exc:
        if documento_creado and documento:
            eliminar_archivo(documento.archivo.storage, documento.archivo.name)
        raise PostulacionInvalida("Este currículum ya fue enviado a esta vacante.") from exc
    except Exception:
        if documento_creado and documento:
            eliminar_archivo(documento.archivo.storage, documento.archivo.name)
        raise
    return postulacion
