import logging
from dataclasses import dataclass, field
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from documentos.models import Documento, IntentoRecepcionDocumento, EstadoDocumento
from .validacion_pdf import validar_pdf
from .almacenamiento import eliminar_archivo
logger = logging.getLogger(__name__)
@dataclass
class DocumentoRecibido:
    origen: str; nombre_original: str; contenido: bytes; mime_type: str
    id_mensaje_origen: str | None = None; remitente: str | None = None; correo: str | None = None; telefono: str | None = None; metadata: dict = field(default_factory=dict)
def _registrar_intento(doc, data):
    IntentoRecepcionDocumento.objects.create(documento=doc, origen=data.origen, id_mensaje_origen=data.id_mensaje_origen or "", remitente=data.remitente or "", correo=data.correo or "", telefono=data.telefono or "", metadata=data.metadata or {})
def recibir_documento(data: DocumentoRecibido) -> tuple[Documento, bool]:
    pdf = validar_pdf(data.nombre_original, data.contenido, data.mime_type)
    existente = Documento.objects.filter(hash_sha256=pdf.hash_sha256).first()
    if existente:
        _registrar_intento(existente, data); logger.info("Documento duplicado hash=%s", pdf.hash_sha256); return existente, True
    doc = Documento(origen=data.origen, id_mensaje_origen=data.id_mensaje_origen or "", nombre_original=pdf.nombre_original, nombre_interno="", mime_type=pdf.mime_type, hash_sha256=pdf.hash_sha256, tamano_bytes=pdf.tamano_bytes, remitente=data.remitente or "", correo=data.correo or "", telefono=data.telefono or "", metadata=data.metadata or {}, estado=EstadoDocumento.PENDIENTE_ANALISIS)
    saved_name = ""
    try:
        with transaction.atomic():
            doc.archivo.save(pdf.nombre_original, ContentFile(pdf.contenido), save=False)
            saved_name = doc.archivo.name; doc.nombre_interno = saved_name.rsplit("/", 1)[-1]; doc.save()
    except IntegrityError:
        eliminar_archivo(doc.archivo.storage, saved_name)
        existente = Documento.objects.get(hash_sha256=pdf.hash_sha256); _registrar_intento(existente, data); return existente, True
    except Exception:
        eliminar_archivo(doc.archivo.storage, saved_name); logger.exception("Error guardando documento"); raise
    logger.info("Documento guardado id=%s origen=%s", doc.pk, doc.origen)
    return doc, False
