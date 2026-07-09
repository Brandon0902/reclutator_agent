import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from documentos.models import Documento, IntentoRecepcionDocumento
@pytest.mark.django_db
def test_admin_carga(django_user_model, client):
    admin = django_user_model.objects.create_superuser("admin", "admin@example.com", "secret"); client.force_login(admin)
    assert client.get(reverse("admin:index")).status_code == 200
    assert client.get(reverse("admin:documentos_documento_changelist")).status_code == 200


@pytest.mark.django_db
def test_admin_duplicado_solo_muestra_advertencia(django_user_model, client, pdf):
    admin = django_user_model.objects.create_superuser("admin", "admin@example.com", "secret")
    client.force_login(admin)
    url = reverse("admin:documentos_documento_add")
    datos = {"metadata": "{}", "estado": "PENDIENTE_ANALISIS", "error": ""}

    primera = client.post(
        url,
        datos | {"archivo": SimpleUploadedFile("cv.pdf", pdf, content_type="application/pdf")},
        follow=True,
    )
    assert primera.status_code == 200
    assert Documento.objects.count() == 1

    duplicada = client.post(
        url,
        datos | {"archivo": SimpleUploadedFile("cv.pdf", pdf, content_type="application/pdf")},
        follow=True,
    )
    textos = [str(mensaje) for mensaje in duplicada.context["messages"]]

    assert Documento.objects.count() == 1
    assert IntentoRecepcionDocumento.objects.count() == 1
    assert textos == ["El documento ya había sido registrado"]


@pytest.mark.django_db
def test_admin_archivo_invalido_muestra_error_en_formulario(django_user_model, client):
    admin = django_user_model.objects.create_superuser("admin", "admin@example.com", "secret")
    client.force_login(admin)

    respuesta = client.post(
        reverse("admin:documentos_documento_add"),
        {
            "archivo": SimpleUploadedFile("imagen.pdf", b"contenido de imagen", content_type="application/pdf"),
            "metadata": "{}",
            "estado": "PENDIENTE_ANALISIS",
            "error": "",
        },
    )

    assert respuesta.status_code == 200
    assert "Firma PDF inválida" in respuesta.content.decode()
    assert Documento.objects.count() == 0
