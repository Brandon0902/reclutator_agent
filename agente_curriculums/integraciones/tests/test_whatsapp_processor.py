from unittest.mock import Mock

import pytest

from documentos.models import Documento, OrigenDocumento
from integraciones.models import EstadoEventoWebhook, EstadoMensajeWhatsApp, EventoWebhook, MensajeWhatsApp
from integraciones.whatsapp.processor import procesar_mensaje_whatsapp


pytestmark = pytest.mark.django_db


def crear_mensaje(tipo="document", mime="application/pdf", wamid="wamid.1"):
    evento = EventoWebhook.objects.create(payload_sha256=(wamid + "0" * 64)[:64])
    return MensajeWhatsApp.objects.create(
        evento=evento, wamid=wamid, tipo=tipo, wa_id="5215512345678",
        nombre_perfil="Candidato", media_id="media-1", nombre_archivo="CV.pdf", mime_type=mime,
    )


def test_descarga_pdf_y_crea_documento(pdf):
    mensaje = crear_mensaje()
    cliente = Mock()
    cliente.obtener_media_url.return_value = "https://meta.example/media"
    cliente.descargar_media.return_value = (pdf, "application/pdf")

    resultado = procesar_mensaje_whatsapp(mensaje.id, cliente=cliente)

    assert resultado.estado == EstadoMensajeWhatsApp.PROCESADO
    assert resultado.documento.origen == OrigenDocumento.WHATSAPP
    assert resultado.documento.telefono == "5215512345678"
    assert resultado.documento.estado == "PENDIENTE_ANALISIS"
    assert EventoWebhook.objects.get(pk=mensaje.evento_id).estado == EstadoEventoWebhook.PROCESADO


def test_pdf_duplicado_reutiliza_documento(pdf):
    primero = crear_mensaje(wamid="wamid.1")
    segundo = crear_mensaje(wamid="wamid.2")
    cliente = Mock()
    cliente.obtener_media_url.return_value = "https://meta.example/media"
    cliente.descargar_media.return_value = (pdf, "application/pdf")

    uno = procesar_mensaje_whatsapp(primero.id, cliente=cliente)
    dos = procesar_mensaje_whatsapp(segundo.id, cliente=cliente)

    assert uno.documento_id == dos.documento_id
    assert Documento.objects.count() == 1
    assert Documento.objects.get().intentos.count() == 1


def test_texto_y_documento_no_pdf_se_ignoran():
    texto = crear_mensaje(tipo="text", wamid="wamid.text")
    imagen = crear_mensaje(mime="image/jpeg", wamid="wamid.image")

    assert procesar_mensaje_whatsapp(texto.id).estado == EstadoMensajeWhatsApp.IGNORADO
    resultado = procesar_mensaje_whatsapp(imagen.id)
    assert resultado.estado == EstadoMensajeWhatsApp.IGNORADO
    assert "PDF" in resultado.error


def test_error_de_meta_queda_reintentable():
    mensaje = crear_mensaje(wamid="wamid.error")
    cliente = Mock()
    cliente.obtener_media_url.side_effect = RuntimeError("Meta no disponible")

    resultado = procesar_mensaje_whatsapp(mensaje.id, cliente=cliente)

    assert resultado.estado == EstadoMensajeWhatsApp.ERROR
    assert "Meta no disponible" in resultado.error
    assert EventoWebhook.objects.get(pk=mensaje.evento_id).estado == EstadoEventoWebhook.ERROR
