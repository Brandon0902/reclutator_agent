import logging

import fitz
from django.db import transaction

from analisis.models import ContenidoExtraido, EstadoExtraccion
from documentos.models import Documento, EstadoDocumento


logger = logging.getLogger(__name__)
MIN_CARACTERES = 100


def extraer_contenido(documento: Documento, forzar: bool = False) -> ContenidoExtraido:
    existente = ContenidoExtraido.objects.filter(documento=documento).first()
    if existente and not forzar and existente.estado == EstadoExtraccion.COMPLETADO:
        return existente

    try:
        with documento.archivo.open("rb") as archivo:
            contenido = archivo.read()
        with fitz.open(stream=contenido, filetype="pdf") as pdf:
            paginas = pdf.page_count
            texto = "\n\n".join(pagina.get_text("text") for pagina in pdf)
        texto = texto.replace("\x00", "").strip()
        caracteres = len("".join(texto.split()))
        estado = EstadoExtraccion.COMPLETADO if caracteres >= MIN_CARACTERES else EstadoExtraccion.SIN_TEXTO
        registro, _ = ContenidoExtraido.objects.update_or_create(
            documento=documento,
            defaults={"texto": texto, "paginas": paginas, "caracteres": caracteres, "estado": estado, "error": ""},
        )
        if estado == EstadoExtraccion.SIN_TEXTO:
            Documento.objects.filter(pk=documento.pk).update(estado=EstadoDocumento.SIN_TEXTO)
        logger.info("Texto extraído documento=%s paginas=%s caracteres=%s estado=%s", documento.pk, paginas, caracteres, estado)
        return registro
    except Exception as exc:
        ContenidoExtraido.objects.update_or_create(
            documento=documento,
            defaults={"texto": "", "paginas": 0, "caracteres": 0, "estado": EstadoExtraccion.ERROR, "error": str(exc)[:2000]},
        )
        Documento.objects.filter(pk=documento.pk).update(estado=EstadoDocumento.ERROR_ANALISIS, error=str(exc)[:2000])
        logger.exception("Error extrayendo texto documento=%s", documento.pk)
        raise
