from datetime import datetime, timezone


def _fecha_meta(valor):
    try:
        return datetime.fromtimestamp(int(valor), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def extraer_mensajes(payload: dict) -> list[dict]:
    encontrados = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contactos = {
                item.get("wa_id"): (item.get("profile") or {}).get("name", "")
                for item in value.get("contacts", []) if item.get("wa_id")
            }
            for mensaje in value.get("messages", []):
                wamid = str(mensaje.get("id", ""))[:255]
                if not wamid:
                    continue
                tipo = str(mensaje.get("type", "unknown"))[:30]
                documento = mensaje.get("document") or {}
                wa_id = str(mensaje.get("from", ""))[:50]
                encontrados.append({
                    "wamid": wamid,
                    "tipo": tipo,
                    "wa_id": wa_id,
                    "nombre_perfil": str(contactos.get(wa_id, ""))[:255],
                    "contenido_texto": str((mensaje.get("text") or {}).get("body", ""))[:4000] if tipo == "text" else "",
                    "media_id": str(documento.get("id", ""))[:255] if tipo == "document" else "",
                    "nombre_archivo": str(documento.get("filename", ""))[:255] if tipo == "document" else "",
                    "mime_type": str(documento.get("mime_type", ""))[:100] if tipo == "document" else "",
                    "timestamp_meta": _fecha_meta(mensaje.get("timestamp")),
                })
    return encontrados


def resumen_sanitizado(payload: dict, mensajes: list[dict]) -> dict:
    return {
        "object": str(payload.get("object", ""))[:80],
        "entry_count": len(payload.get("entry", [])),
        "message_count": len(mensajes),
        "message_types": sorted({item["tipo"] for item in mensajes}),
    }
