# Configuración inicial de WhatsApp Cloud API

Esta guía cubre los entregables 1 y 2: número de prueba, verificación del webhook y registro seguro de eventos. La descarga de PDFs se implementará en el entregable 3.

## 1. Crear la aplicación de Meta

1. Acceder a Meta for Developers.
2. Crear una aplicación de tipo Business.
3. Agregar el producto WhatsApp.
4. Conservar para pruebas el número temporal proporcionado por Meta.
5. Registrar únicamente números destinatarios autorizados durante el modo de prueba.

No conectar todavía el número principal de la empresa.

## 2. Variables locales

Copiar `.env.example` a `.env` y completar localmente:

```env
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_APP_SECRET=
WHATSAPP_GRAPH_VERSION=
WHATSAPP_VALIDATE_SIGNATURE=true
WHATSAPP_MAX_DOCUMENT_SIZE_MB=15
WHATSAPP_WEBHOOK_MAX_BODY_KB=512
```

Nunca colocar valores reales en Git, documentación, capturas o logs.

## 3. Exponer Django por HTTPS

Con Django disponible en `http://127.0.0.1:8000`, iniciar un túnel:

```powershell
ngrok http 8000
```

o:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

Callback:

```text
https://SUBDOMINIO-TEMPORAL/api/webhooks/whatsapp/
```

## 4. Configurar el webhook en Meta

1. Registrar la URL pública como Callback URL.
2. Introducir exactamente el mismo `WHATSAPP_VERIFY_TOKEN`.
3. Completar la verificación GET.
4. Suscribir el campo `messages` de la cuenta de WhatsApp Business.

## 5. Comportamiento implementado

- Rechaza firmas inválidas con HTTP 403.
- Rechaza JSON inválido con HTTP 400.
- Limita el tamaño del body.
- Guarda un hash único del evento.
- Registra mensajes de texto y documentos.
- Conserva metadatos del documento, pero no descarga todavía el archivo.
- Registra eventos irrelevantes como ignorados.
- Responde HTTP 200 a eventos válidos y duplicados.
- No guarda tokens, firmas ni archivos binarios en los eventos.

## 6. Verificación operativa

Después de recibir un mensaje, revisar Django Admin:

```text
Integraciones → Eventos webhook
Integraciones → Mensajes WhatsApp
```

En esta etapa el estado esperado del mensaje es `RECIBIDO`. La descarga y transición a procesamiento se agregarán en el entregable 3.

## 7. Producción

Con `DEBUG=false`, `manage.py check` produce error si faltan secretos obligatorios o si la validación de firma está desactivada. Para producción se debe usar un token de sistema permanente, HTTPS estable y rotación documentada de secretos.
