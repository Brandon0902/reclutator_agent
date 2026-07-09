from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import override_settings

from documentos.models import Documento, IntentoRecepcionDocumento, OrigenDocumento
from integraciones.models import MensajeExternoProcesado
from integraciones.services.imap_client import AdjuntoIMAP, IMAPClient, MensajeIMAP


def mensaje(uid: str, adjuntos: list[AdjuntoIMAP]) -> MensajeIMAP:
    return MensajeIMAP(
        uid=uid,
        clave=f"99:{uid}",
        message_id=f"<{uid}@example.com>",
        asunto="Currículum",
        remitente="Persona Candidata",
        correo="persona@example.com",
        fecha="Sat, 04 Jul 2026 10:00:00 -0600",
        adjuntos_pdf=adjuntos,
    )


def cliente_mock(mock_client, uids: list[str]):
    cliente = Mock()
    cliente.folder = "INBOX"
    cliente.uidvalidity = "99"
    cliente.buscar_no_leidos.return_value = uids
    cliente.clave_mensaje.side_effect = lambda uid: f"99:{uid}"
    mock_client.return_value.__enter__.return_value = cliente
    return cliente


@pytest.mark.django_db
@patch("integraciones.management.commands.importar_correos_imap.IMAPClient")
def test_dry_run_no_modifica_buzon_ni_base(mock_client, capsys):
    cliente = cliente_mock(mock_client, ["1", "2"])
    call_command("importar_correos_imap", "--dry-run", "--limit", "2")
    assert "No leídos encontrados: 2" in capsys.readouterr().out
    cliente.obtener_mensaje.assert_not_called()
    cliente.marcar_como_leido.assert_not_called()
    assert MensajeExternoProcesado.objects.count() == 0


@pytest.mark.django_db
@patch("integraciones.management.commands.importar_correos_imap.IMAPClient")
def test_importa_pdf_y_marca_mensaje_leido(mock_client, pdf):
    cliente = cliente_mock(mock_client, ["1"])
    cliente.obtener_mensaje.return_value = mensaje("1", [AdjuntoIMAP("cv.pdf", "application/pdf", pdf)])
    call_command("importar_correos_imap", "--limit", "1")
    documento = Documento.objects.get()
    assert documento.origen == OrigenDocumento.IMAP
    assert documento.correo == "persona@example.com"
    assert documento.id_mensaje_origen == "99:1"
    assert MensajeExternoProcesado.objects.get().estado == "PROCESADO"
    cliente.marcar_como_leido.assert_called_once_with("1")


@pytest.mark.django_db
@patch("integraciones.management.commands.importar_correos_imap.IMAPClient")
def test_importa_varios_pdf_y_detecta_duplicado(mock_client, pdf):
    cliente = cliente_mock(mock_client, ["1", "2"])
    otro_pdf = b"%PDF-1.4\notro contenido\n%%EOF"
    cliente.obtener_mensaje.side_effect = [
        mensaje("1", [AdjuntoIMAP("uno.pdf", "application/pdf", pdf), AdjuntoIMAP("dos.pdf", "application/pdf", otro_pdf)]),
        mensaje("2", [AdjuntoIMAP("repetido.pdf", "application/pdf", pdf)]),
    ]
    call_command("importar_correos_imap", "--limit", "2")
    assert Documento.objects.count() == 2
    assert IntentoRecepcionDocumento.objects.count() == 1
    assert MensajeExternoProcesado.objects.filter(estado="PROCESADO").count() == 2
    assert cliente.marcar_como_leido.call_count == 2


@pytest.mark.django_db
@patch("integraciones.management.commands.importar_correos_imap.IMAPClient")
def test_ignora_mensaje_sin_pdf_y_no_lo_marca_leido(mock_client):
    cliente = cliente_mock(mock_client, ["1"])
    cliente.obtener_mensaje.return_value = mensaje("1", [])
    call_command("importar_correos_imap")
    assert MensajeExternoProcesado.objects.get().estado == "IGNORADO"
    cliente.marcar_como_leido.assert_not_called()


@pytest.mark.django_db
@patch("integraciones.management.commands.importar_correos_imap.IMAPClient")
def test_adjunto_invalido_registra_error_y_se_puede_reintentar(mock_client, pdf):
    cliente = cliente_mock(mock_client, ["1"])
    cliente.obtener_mensaje.return_value = mensaje("1", [AdjuntoIMAP("cv.pdf", "application/pdf", b"no es pdf")])
    call_command("importar_correos_imap")
    registro = MensajeExternoProcesado.objects.get()
    assert registro.estado == "ERROR"
    cliente.marcar_como_leido.assert_not_called()

    cliente.obtener_mensaje.return_value = mensaje("1", [AdjuntoIMAP("cv.pdf", "application/pdf", pdf)])
    call_command("importar_correos_imap")
    registro.refresh_from_db()
    assert registro.estado == "PROCESADO"
    assert Documento.objects.count() == 1
    cliente.marcar_como_leido.assert_called_once_with("1")


@override_settings(IMAP_HOST="", IMAP_USERNAME="", IMAP_PASSWORD="")
def test_cliente_rechaza_credenciales_faltantes():
    with pytest.raises(ImproperlyConfigured, match="Faltan IMAP_HOST"):
        IMAPClient()
