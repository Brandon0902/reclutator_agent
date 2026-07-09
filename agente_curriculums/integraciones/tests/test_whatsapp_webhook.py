import hashlib
import hmac
import json

import pytest

from documentos.models import Documento
from integraciones.checks import whatsapp_configuration_check
from integraciones.models import EstadoEventoWebhook, EventoWebhook, MensajeWhatsApp


pytestmark = pytest.mark.django_db


def firma(body, secret="secret"):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def post_firmado(client, payload, settings, secret="secret"):
    settings.WHATSAPP_APP_SECRET = secret
    settings.WHATSAPP_VALIDATE_SIGNATURE = True
    body = json.dumps(payload, separators=(",", ":")).encode()
    return client.post(
        "/api/webhooks/whatsapp/", data=body, content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=firma(body, secret),
    )


def payload_mensaje(mensaje, contacto=True):
    value = {"messages": [mensaje]}
    if contacto:
        value["contacts"] = [{"wa_id": mensaje.get("from"), "profile": {"name": "Candidato Prueba"}}]
    return {"object": "whatsapp_business_account", "entry": [{"id": "waba", "changes": [{"field": "messages", "value": value}]}]}


def test_verificacion_get(client, settings):
    settings.WHATSAPP_VERIFY_TOKEN = "token"
    correcta = client.get("/api/webhooks/whatsapp/", {
        "hub.mode": "subscribe", "hub.verify_token": "token", "hub.challenge": "123",
    })
    assert correcta.status_code == 200 and correcta.content == b"123"
    assert client.get("/api/webhooks/whatsapp/", {"hub.mode": "subscribe", "hub.verify_token": "bad"}).status_code == 403
    assert client.get("/api/webhooks/whatsapp/", {"hub.mode": "otro", "hub.verify_token": "token"}).status_code == 403


def test_token_vacio_no_verifica(client, settings):
    settings.WHATSAPP_VERIFY_TOKEN = ""
    assert client.get("/api/webhooks/whatsapp/", {"hub.mode": "subscribe", "hub.verify_token": ""}).status_code == 403


def test_firma_invalida_no_registra_evento(client, settings):
    settings.WHATSAPP_APP_SECRET = "secret"
    settings.WHATSAPP_VALIDATE_SIGNATURE = True
    respuesta = client.post(
        "/api/webhooks/whatsapp/", data="{}", content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256="sha256=bad",
    )
    assert respuesta.status_code == 403
    assert EventoWebhook.objects.count() == 0


def test_registra_mensaje_texto_y_payload_sanitizado(client, settings):
    payload = payload_mensaje({
        "id": "wamid.texto", "from": "5215512345678", "timestamp": "1760000000",
        "type": "text", "text": {"body": "Hola, VAC-REC-001"},
    })
    respuesta = post_firmado(client, payload, settings)
    assert respuesta.status_code == 200 and respuesta.json()["duplicate"] is False
    evento = EventoWebhook.objects.get()
    mensaje = MensajeWhatsApp.objects.get()
    assert evento.estado == EstadoEventoWebhook.RECIBIDO
    assert evento.payload_sanitizado == {
        "object": "whatsapp_business_account", "entry_count": 1,
        "message_count": 1, "message_types": ["text"],
    }
    assert "5215512345678" not in json.dumps(evento.payload_sanitizado)
    assert mensaje.wamid == "wamid.texto"
    assert mensaje.contenido_texto == "Hola, VAC-REC-001"
    assert mensaje.nombre_perfil == "Candidato Prueba"


def test_documento_solo_se_registra_sin_descargar(client, settings):
    payload = payload_mensaje({
        "id": "wamid.pdf", "from": "5215512345678", "timestamp": "1760000000", "type": "document",
        "document": {"id": "media-123", "filename": "CV.pdf", "mime_type": "application/pdf"},
    })
    respuesta = post_firmado(client, payload, settings)
    assert respuesta.status_code == 200
    mensaje = MensajeWhatsApp.objects.get()
    assert (mensaje.media_id, mensaje.nombre_archivo, mensaje.mime_type) == ("media-123", "CV.pdf", "application/pdf")
    assert Documento.objects.count() == 0


def test_evento_y_mensaje_duplicados_son_idempotentes(client, settings):
    payload = payload_mensaje({"id": "wamid.duplicado", "from": "52155", "type": "text", "text": {"body": "Hola"}})
    primera = post_firmado(client, payload, settings)
    segunda = post_firmado(client, payload, settings)
    assert primera.json()["duplicate"] is False
    assert segunda.json()["duplicate"] is True
    assert EventoWebhook.objects.count() == 1
    assert MensajeWhatsApp.objects.count() == 1


def test_mismo_wamid_en_otro_evento_no_duplica_mensaje(client, settings):
    mensaje = {"id": "wamid.unico", "from": "52155", "type": "text", "text": {"body": "Hola"}}
    post_firmado(client, payload_mensaje(mensaje), settings)
    segundo_payload = payload_mensaje(mensaje)
    segundo_payload["entry"][0]["id"] = "otro-waba"
    post_firmado(client, segundo_payload, settings)
    assert EventoWebhook.objects.count() == 2
    assert MensajeWhatsApp.objects.count() == 1


def test_evento_sin_mensajes_queda_ignorado(client, settings):
    payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {"statuses": [{"id": "x"}]}}]}]}
    assert post_firmado(client, payload, settings).status_code == 200
    evento = EventoWebhook.objects.get()
    assert evento.estado == EstadoEventoWebhook.IGNORADO and evento.procesado_at


def test_json_invalido_y_body_excesivo(client, settings):
    settings.WHATSAPP_APP_SECRET = "secret"
    settings.WHATSAPP_VALIDATE_SIGNATURE = True
    body = b"no-json"
    respuesta = client.post(
        "/api/webhooks/whatsapp/", data=body, content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=firma(body),
    )
    assert respuesta.status_code == 400
    settings.WHATSAPP_WEBHOOK_MAX_BODY_KB = 0
    assert post_firmado(client, {"entry": []}, settings).status_code == 413


def test_check_produccion_exige_secretos_y_firma(settings):
    settings.DEBUG = False
    settings.WHATSAPP_VERIFY_TOKEN = ""
    settings.WHATSAPP_APP_SECRET = ""
    settings.WHATSAPP_ACCESS_TOKEN = ""
    settings.WHATSAPP_PHONE_NUMBER_ID = ""
    settings.WHATSAPP_GRAPH_VERSION = ""
    settings.WHATSAPP_VALIDATE_SIGNATURE = False
    ids = {issue.id for issue in whatsapp_configuration_check(None)}
    assert ids == {"integraciones.E001", "integraciones.E002"}
