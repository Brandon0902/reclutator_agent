import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
@pytest.mark.django_db
def test_health_publico(): assert APIClient().get("/api/health/").json() == {"status": "ok"}
@pytest.mark.django_db
def test_documentos_protegidos(): assert APIClient().get("/api/documentos/").status_code in (401, 403)
@pytest.mark.django_db
def test_upload_listado_filtros_busqueda_descarga(usuario, pdf):
    c = APIClient(); c.force_authenticate(usuario)
    r = c.post("/api/documentos/upload/", {"archivo": SimpleUploadedFile("cv.pdf", pdf, content_type="application/pdf"), "remitente": "Ana"}, format="multipart")
    assert r.status_code == 201 and not r.json()["duplicado"]
    pk = r.json()["id"]
    assert c.get("/api/documentos/?origen=MANUAL&search=Ana").json()["count"] == 1
    assert c.get(f"/api/documentos/{pk}/").status_code == 200
    assert c.get(f"/api/documentos/{pk}/archivo/").status_code == 200
    dup = c.post("/api/documentos/upload/", {"archivo": SimpleUploadedFile("otro.pdf", pdf, content_type="application/pdf")}, format="multipart")
    assert dup.status_code == 200 and dup.json()["duplicado"]
@pytest.mark.django_db
def test_documento_inexistente(usuario):
    c=APIClient(); c.force_authenticate(usuario); assert c.get("/api/documentos/999/").status_code == 404
