import hashlib
from dataclasses import dataclass
from pathlib import Path
from django.conf import settings
from django.utils.text import get_valid_filename
from documentos.exceptions import DocumentoInvalidoError

@dataclass(frozen=True)
class PDFValidado:
    nombre_original: str; contenido: bytes; mime_type: str; hash_sha256: str; tamano_bytes: int
def validar_pdf(nombre: str, contenido: bytes, mime_type: str) -> PDFValidado:
    limpio = get_valid_filename(Path(nombre).name)
    if not limpio or Path(limpio).suffix.lower() != ".pdf": raise DocumentoInvalidoError("La extensión debe ser .pdf")
    if mime_type.lower().split(";", 1)[0].strip() != "application/pdf": raise DocumentoInvalidoError("MIME type inválido")
    if not contenido: raise DocumentoInvalidoError("El archivo está vacío")
    if len(contenido) > settings.MAX_PDF_SIZE_MB * 1024 * 1024: raise DocumentoInvalidoError("El archivo supera el tamaño máximo")
    if not contenido.startswith(b"%PDF-"): raise DocumentoInvalidoError("Firma PDF inválida")
    return PDFValidado(limpio, contenido, "application/pdf", hashlib.sha256(contenido).hexdigest(), len(contenido))
