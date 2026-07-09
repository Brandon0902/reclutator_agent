from unittest.mock import patch
import pytest
from django.core.management import call_command
@pytest.mark.django_db
@patch("integraciones.management.commands.importar_correos_outlook.MicrosoftGraphClient")
def test_comando_outlook(mock_client, pdf):
    c=mock_client.return_value; c.obtener_mensajes_con_adjuntos.return_value=[{"id":"m1", "subject":"CV"}]; c.obtener_adjuntos.return_value=[{"id":"a1","name":"cv.pdf","contentType":"application/pdf"}]; c.descargar_adjunto.return_value=pdf
    call_command("importar_correos_outlook")
