from types import SimpleNamespace
from unittest.mock import patch

import fitz
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from documentos.models import Documento
from postulaciones.models import EstadoPostulacion, Postulacion
from postulaciones.services import recibir_postulacion
from vacantes.models import Vacante


def pdf_valido():
    documento = fitz.open()
    documento.new_page().insert_text((72, 72), "Currículum de prueba")
    contenido = documento.tobytes()
    documento.close()
    return SimpleUploadedFile("cv.pdf", contenido, content_type="application/pdf")


@pytest.mark.django_db
def test_vacante_no_publicada_no_expone_formulario(usuario):
    vacante = Vacante.objects.create(propietario=usuario, titulo="Backend")
    response = APIClient().get(f"/api/postulaciones/public/vacantes/{vacante.public_slug}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_formulario_general_es_publico_y_solo_solicita_pdf():
    client = APIClient()
    page = client.get("/aplicar/")
    assert page.status_code == 200
    assert b'name="archivo"' in page.content
    assert b'name="nombre_completo"' not in page.content
    assert b'name="telefono_whatsapp"' not in page.content
    assert b'name="correo"' not in page.content
    assert b'name="vacante_interes"' not in page.content
    response = client.post(
        "/api/postulaciones/public/curriculums/",
        {"archivo": pdf_valido(), "consentimiento": "true"},
        format="multipart",
    )
    assert response.status_code == 201
    documento = Documento.objects.get()
    assert documento.origen == "FORMULARIO_WEB"
    assert documento.estado == "PENDIENTE_ANALISIS"
    assert documento.metadata["consentimiento_datos"] is True
    assert documento.metadata["consentimiento_version"] == "curriculum-v1"
    assert Postulacion.objects.count() == 0


@pytest.mark.django_db
def test_formulario_general_deduplica_el_mismo_pdf():
    client = APIClient()
    contenido = pdf_valido().read()
    primero = client.post(
        "/api/postulaciones/public/curriculums/",
        {"archivo": SimpleUploadedFile("cv.pdf", contenido, content_type="application/pdf"), "consentimiento": "true"},
        format="multipart",
    )
    segundo = client.post(
        "/api/postulaciones/public/curriculums/",
        {"archivo": SimpleUploadedFile("cv.pdf", contenido, content_type="application/pdf"), "consentimiento": "true"},
        format="multipart",
    )
    assert primero.status_code == 201
    assert segundo.status_code == 200
    assert segundo.data["duplicado"] is True
    assert Documento.objects.count() == 1
    assert Postulacion.objects.count() == 0


@pytest.mark.django_db
def test_formulario_general_rechaza_pdf_sin_consentimiento():
    response = APIClient().post(
        "/api/postulaciones/public/curriculums/",
        {"archivo": pdf_valido()},
        format="multipart",
    )
    assert response.status_code == 400
    assert Documento.objects.count() == 0


@pytest.mark.django_db
def test_recibe_postulacion_publica_y_guarda_relaciones(usuario):
    vacante = Vacante.objects.create(propietario=usuario, titulo="Backend", publicada=True)
    client = APIClient()
    response = client.post(
        f"/api/postulaciones/public/vacantes/{vacante.public_slug}/postulaciones/",
        {"nombre_completo": "Ana Pérez", "telefono_whatsapp": "+5215555555555", "correo": "ana@example.com", "archivo": pdf_valido(), "consentimiento": "true"},
        format="multipart",
    )
    assert response.status_code == 201
    postulacion = Postulacion.objects.get()
    assert postulacion.estado == EstadoPostulacion.RECIBIDO
    assert postulacion.vacante_id == vacante.id
    assert postulacion.consentimiento_datos is True
    assert Documento.objects.get().origen == "FORMULARIO_WEB"


@pytest.mark.django_db
def test_rechaza_postulacion_sin_consentimiento(usuario):
    vacante = Vacante.objects.create(propietario=usuario, titulo="Backend", publicada=True)
    response = APIClient().post(
        f"/api/postulaciones/public/vacantes/{vacante.public_slug}/postulaciones/",
        {"nombre_completo": "Ana Pérez", "telefono_whatsapp": "+5215555555555", "correo": "ana@example.com", "archivo": pdf_valido(), "consentimiento": "false"},
        format="multipart",
    )
    assert response.status_code == 400
    assert Postulacion.objects.count() == 0


@pytest.mark.django_db
def test_panel_filtra_y_descarga_solo_con_usuario_autorizado(usuario):
    vacante = Vacante.objects.create(propietario=usuario, titulo="Backend", publicada=True)
    public = APIClient()
    public.post(
        f"/api/postulaciones/public/vacantes/{vacante.public_slug}/postulaciones/",
        {"nombre_completo": "Ana Pérez", "telefono_whatsapp": "+5215555555555", "correo": "ana@example.com", "archivo": pdf_valido(), "consentimiento": "true"},
        format="multipart",
    )
    postulacion = Postulacion.objects.get()
    rh = APIClient()
    assert rh.get("/api/postulaciones/").status_code == 403
    usuario.is_staff = True
    usuario.save(update_fields=["is_staff"])
    rh.force_authenticate(usuario)
    assert rh.get("/api/postulaciones/?estado=RECIBIDO").status_code == 200
    response = rh.get(f"/api/postulaciones/{postulacion.pk}/archivo/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"


@pytest.mark.django_db
def test_rh_no_puede_ver_postulaciones_de_otro_propietario(usuario, django_user_model):
    vacante = Vacante.objects.create(propietario=usuario, titulo="Backend", publicada=True)
    APIClient().post(
        f"/api/postulaciones/public/vacantes/{vacante.public_slug}/postulaciones/",
        {"nombre_completo": "Ana Pérez", "telefono_whatsapp": "+5215555555555", "correo": "ana@example.com", "archivo": pdf_valido(), "consentimiento": "true"},
        format="multipart",
    )
    otro = django_user_model.objects.create_user("otro-rh", password="secret", is_staff=True)
    client = APIClient()
    client.force_authenticate(otro)
    assert client.get("/api/postulaciones/").data["count"] == 0
    assert client.get(f"/api/postulaciones/{Postulacion.objects.get().pk}/archivo/").status_code == 404


@pytest.mark.django_db
def test_error_posterior_elimina_pdf_huerfano(usuario, settings):
    vacante = Vacante.objects.create(propietario=usuario, titulo="Backend", publicada=True)
    request = SimpleNamespace(data={}, META={"REMOTE_ADDR": "127.0.0.88", "HTTP_USER_AGENT": "pytest"})
    archivo = pdf_valido()
    with patch("postulaciones.services.Postulacion.objects.create", side_effect=RuntimeError("forzado")):
        with pytest.raises(RuntimeError):
            recibir_postulacion(
                vacante=vacante, nombre="Ana", telefono="555", correo="orphan@example.com",
                archivo=archivo, consentimiento=True, request=request,
            )
    assert Documento.objects.count() == 0
    assert not list(settings.MEDIA_ROOT.rglob("*.pdf"))


@pytest.mark.django_db
def test_rate_limit_persiste_entre_solicitudes(usuario, settings):
    settings.PUBLIC_FORM_RATE_LIMIT = 1
    vacante = Vacante.objects.create(propietario=usuario, titulo="Backend", publicada=True)
    client = APIClient()
    payload = {"nombre_completo": "Ana", "telefono_whatsapp": "555", "correo": "limit@example.com", "consentimiento": "true"}
    primera = client.post(
        f"/api/postulaciones/public/vacantes/{vacante.public_slug}/postulaciones/",
        payload | {"archivo": SimpleUploadedFile("bad.pdf", b"%PDF-bad", content_type="application/pdf")}, format="multipart",
    )
    segunda = client.post(
        f"/api/postulaciones/public/vacantes/{vacante.public_slug}/postulaciones/",
        payload | {"archivo": pdf_valido()}, format="multipart",
    )
    assert primera.status_code == 400
    assert segunda.status_code == 400
    assert "límite" in segunda.data["detail"]


@pytest.mark.django_db
def test_formulario_renderiza_turnstile_cuando_esta_activo(usuario, settings):
    settings.TURNSTILE_ENABLED = True
    settings.TURNSTILE_SITE_KEY = "site-key-test"
    vacante = Vacante.objects.create(propietario=usuario, titulo="Backend", publicada=True)
    response = APIClient().get(f"/aplicar/{vacante.public_slug}/")
    assert response.status_code == 200
    assert b"cf-turnstile" in response.content
    assert b"site-key-test" in response.content
