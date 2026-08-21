import imaplib
import re
import ssl
from dataclasses import dataclass, field
from email import policy
from email.header import decode_header, make_header
from email.parser import BytesParser
from email.utils import parseaddr
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class AdjuntoIMAP:
    nombre: str
    mime_type: str
    contenido: bytes


@dataclass(frozen=True)
class MensajeIMAP:
    uid: str
    clave: str
    message_id: str
    asunto: str
    remitente: str
    correo: str
    fecha: str
    adjuntos_pdf: list[AdjuntoIMAP] = field(default_factory=list)


def _decodificar(valor: str | None) -> str:
    if not valor:
        return ""
    try:
        return str(make_header(decode_header(valor)))
    except (LookupError, UnicodeError):
        return valor


class IMAPClient:
    def __init__(self):
        self.host = settings.IMAP_HOST
        self.port = settings.IMAP_PORT
        self.username = settings.IMAP_USERNAME
        self.password = settings.IMAP_PASSWORD
        self.folder = settings.IMAP_FOLDER
        self.use_ssl = settings.IMAP_USE_SSL
        self.connection: imaplib.IMAP4 | None = None
        self.uidvalidity = ""
        if not all([self.host, self.username, self.password]):
            raise ImproperlyConfigured("Faltan IMAP_HOST, IMAP_USERNAME o IMAP_PASSWORD")

    def __enter__(self):
        self.conectar()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.cerrar()

    def conectar(self) -> None:
        if self.use_ssl:
            self.connection = imaplib.IMAP4_SSL(
                self.host,
                self.port,
                ssl_context=ssl.create_default_context(),
                timeout=30,
            )
        else:
            self.connection = imaplib.IMAP4(self.host, self.port, timeout=30)
        self.connection.login(self.username, self.password)
        estado, datos = self.connection.status(self.folder, "(UIDVALIDITY)")
        if estado != "OK" or not datos or not datos[0]:
            raise imaplib.IMAP4.error(f"No se pudo consultar la carpeta {self.folder}")
        coincidencia = re.search(rb"UIDVALIDITY\s+(\d+)", datos[0])
        if not coincidencia:
            raise imaplib.IMAP4.error("El servidor no devolvió UIDVALIDITY")
        self.uidvalidity = coincidencia.group(1).decode("ascii")
        estado, _ = self.connection.select(self.folder, readonly=False)
        if estado != "OK":
            raise imaplib.IMAP4.error(f"No se pudo abrir la carpeta {self.folder}")

    def cerrar(self) -> None:
        if not self.connection:
            return
        try:
            self.connection.close()
        except imaplib.IMAP4.error:
            pass
        try:
            self.connection.logout()
        except imaplib.IMAP4.error:
            pass
        self.connection = None

    def buscar_no_leidos(self, limit: int) -> list[str]:
        if not self.connection:
            raise RuntimeError("El cliente IMAP no está conectado")
        estado, datos = self.connection.uid("search", None, "UNSEEN")
        if estado != "OK":
            raise imaplib.IMAP4.error("No se pudieron buscar mensajes no leídos")
        uids = datos[0].split() if datos and datos[0] else []
        return [uid.decode("ascii") for uid in uids[:limit]]

    def buscar_todos(self, limit: int) -> list[str]:
        if not self.connection:
            raise RuntimeError("El cliente IMAP no esta conectado")
        estado, datos = self.connection.uid("search", None, "ALL")
        if estado != "OK":
            raise imaplib.IMAP4.error("No se pudieron buscar todos los mensajes")
        uids = datos[0].split() if datos and datos[0] else []
        return [uid.decode("ascii") for uid in uids[:limit]]

    def clave_mensaje(self, uid: str) -> str:
        return f"{self.uidvalidity}:{uid}"

    def obtener_mensaje(self, uid: str) -> MensajeIMAP:
        if not self.connection:
            raise RuntimeError("El cliente IMAP no está conectado")
        estado, datos = self.connection.uid("fetch", uid, "(BODY.PEEK[])")
        if estado != "OK":
            raise imaplib.IMAP4.error(f"No se pudo descargar el mensaje UID {uid}")
        crudo = next((item[1] for item in datos if isinstance(item, tuple) and len(item) > 1), None)
        if not crudo:
            raise imaplib.IMAP4.error(f"El mensaje UID {uid} llegó vacío")

        mensaje = BytesParser(policy=policy.default).parsebytes(crudo)
        nombre_remitente, correo = parseaddr(mensaje.get("From", ""))
        adjuntos: list[AdjuntoIMAP] = []
        for parte in mensaje.walk():
            nombre = parte.get_filename()
            if not nombre:
                continue
            nombre = _decodificar(nombre)
            mime_type = parte.get_content_type().lower()
            if Path(nombre).suffix.lower() != ".pdf" and mime_type != "application/pdf":
                continue
            contenido = parte.get_payload(decode=True) or b""
            adjuntos.append(AdjuntoIMAP(nombre=nombre, mime_type=mime_type, contenido=contenido))

        return MensajeIMAP(
            uid=uid,
            clave=self.clave_mensaje(uid),
            message_id=str(mensaje.get("Message-ID", "")).strip(),
            asunto=_decodificar(mensaje.get("Subject")),
            remitente=_decodificar(nombre_remitente),
            correo=correo,
            fecha=str(mensaje.get("Date", "")),
            adjuntos_pdf=adjuntos,
        )

    def marcar_como_leido(self, uid: str) -> None:
        if not self.connection:
            raise RuntimeError("El cliente IMAP no está conectado")
        estado, _ = self.connection.uid("store", uid, "+FLAGS.SILENT", "(\\Seen)")
        if estado != "OK":
            raise imaplib.IMAP4.error(f"No se pudo marcar como leído el mensaje UID {uid}")
