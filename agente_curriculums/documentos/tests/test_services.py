import hashlib
import pytest
from documentos.exceptions import DocumentoInvalidoError
from documentos.models import Documento, IntentoRecepcionDocumento, OrigenDocumento
from documentos.services import DocumentoRecibido, recibir_documento
@pytest.mark.django_db
def test_guarda_hash_uuid_y_detecta_duplicado(pdf):
    data = DocumentoRecibido(OrigenDocumento.MANUAL, "../CV Persona.pdf", pdf, "application/pdf")
    doc, duplicate = recibir_documento(data)
    assert not duplicate and doc.hash_sha256 == hashlib.sha256(pdf).hexdigest()
    assert doc.nombre_original == "CV_Persona.pdf" and doc.archivo.name.startswith("curriculums/") and doc.archivo.name.endswith(".pdf")
    again, duplicate = recibir_documento(data)
    assert duplicate and again.pk == doc.pk and Documento.objects.count() == 1 and IntentoRecepcionDocumento.objects.count() == 1
@pytest.mark.parametrize("name,content,mime", [("x.txt", b"%PDF-1.4", "application/pdf"), ("x.pdf", b"hello", "application/pdf"), ("x.pdf", b"", "application/pdf"), ("x.pdf", b"%PDF-1.4", "text/plain")])
def test_rechaza_invalidos(name, content, mime):
    with pytest.raises(DocumentoInvalidoError): recibir_documento(DocumentoRecibido("MANUAL", name, content, mime))
@pytest.mark.django_db
def test_rechaza_demasiado_grande(settings):
    settings.MAX_PDF_SIZE_MB = 0
    with pytest.raises(DocumentoInvalidoError): recibir_documento(DocumentoRecibido("MANUAL", "x.pdf", b"%PDF-1.4", "application/pdf"))
