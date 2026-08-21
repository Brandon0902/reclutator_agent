# Agente Currículums

MVP Django para recibir, validar, deduplicar y administrar currículums PDF de carga manual, Microsoft 365 y WhatsApp Cloud API. Los archivos privados se guardan bajo `media/curriculums/YYYY/MM/` con UUID; la lógica compartida vive en `documentos/services`.

## Arquitectura y seguridad

`documentos` contiene modelos, Admin, API y servicio transaccional. `integraciones` contiene clientes externos, webhook y control de mensajes procesados. Se validan extensión, MIME, firma `%PDF-`, tamaño, nombre y SHA-256. No se exponen rutas internas ni secretos; producción no sirve `MEDIA_ROOT`. Modelos: `Documento`, `IntentoRecepcionDocumento`, `MensajeExternoProcesado`. Grupos: Administrador, Recursos Humanos y Solo lectura.

## Instalación en Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d
python manage.py migrate
python manage.py createsuperuser
python manage.py crear_grupos_iniciales
python manage.py runserver
```

Admin en Docker: `http://127.0.0.1:8001/admin/` (puerto configurable con `WEB_PORT`). Salud: `/api/health/`. API autenticada: `/api/documentos/`, `/api/documentos/upload/`, `/api/documentos/{id}/`, `/api/documentos/{id}/archivo/`.

```bash
curl -b cookies.txt -F "archivo=@CV.pdf;type=application/pdf" http://127.0.0.1:8000/api/documentos/upload/
```

```powershell
Invoke-RestMethod -WebSession $session -Uri http://127.0.0.1:8000/api/documentos/upload/ -Method Post -Form @{archivo=Get-Item .\CV.pdf}
```

## Pruebas y operaciones

Ejecute `pytest`, `python manage.py check` y `python manage.py makemigrations --check`.

### Correo IMAP / cPanel

Configure `IMAP_HOST`, `IMAP_PORT`, `IMAP_USERNAME`, `IMAP_PASSWORD`, `IMAP_FOLDER`, `IMAP_USE_SSL` e `IMAP_MARK_AS_READ` en `.env`. La contraseña nunca debe guardarse en Git.

Compruebe la conexión sin modificar el buzón ni la base de datos:

```powershell
python manage.py importar_correos_imap --dry-run --limit 20
```

Importe hasta 20 mensajes no leídos:

```powershell
python manage.py importar_correos_imap --limit 20
```

Los mensajes con PDFs procesados se marcan como leídos; los mensajes sin PDF o con errores permanecen sin cambios. El identificador `UIDVALIDITY:UID` impide reprocesar mensajes ya resueltos.

Para Microsoft 365 se conserva `python manage.py importar_correos_outlook`.

Para Microsoft complete tenant, client, secret y buzón, y conceda permisos Graph. Para Meta complete las variables `WHATSAPP_*`, configure `/api/webhooks/whatsapp/` como callback HTTPS y mantenga activa la validación de firma. Consulte [docs/whatsapp_meta.md](docs/whatsapp_meta.md). El webhook registra los eventos y el worker descarga, valida y almacena los documentos PDF de forma asíncrona.

Pendiente para etapas posteriores: almacenamiento de objetos, OCR e interfaz visual para reclutadores.

## Recepción pública de currículums

El banco general de currículums se alimenta mediante una URL pública fija que no requiere autenticación:

`/aplicar/`

El formulario solicita únicamente un currículum PDF y lo guarda directamente en el banco general de documentos, sin autenticación y sin depender de Meta o WhatsApp. Después, una vacante creada con el agente puede evaluar los documentos guardados. Las rutas anteriores por UUID se conservan internamente por compatibilidad, pero no son necesarias para este flujo.

Docker ejecuta `web` y `worker` con configuración de producción y se niega a iniciar con una `DJANGO_SECRET_KEY` débil. Antes de levantar los servicios, sustituya `change_me` por una clave aleatoria de al menos 50 caracteres y configure `DJANGO_CSRF_TRUSTED_ORIGINS` con el dominio HTTPS definitivo. El gateway público limita las cargas a 20 MB; ClamAV está habilitado por defecto en Compose y Turnstile se activa mediante sus variables de entorno.

## Análisis local con Gemma 4

La fase de análisis extrae texto seleccionable con PyMuPDF y lo evalúa localmente mediante Ollama. Los PDFs escaneados no se convierten en imágenes: quedan marcados como `SIN_TEXTO`. La puntuación ordena candidatos para revisión humana y nunca produce rechazo automático.

Variables principales:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4:e2b-it-qat
OLLAMA_TIMEOUT_SECONDS=600
ANALYSIS_INTERVAL_SECONDS=900
ANALYSIS_BATCH_SIZE=2
```

Para levantar MySQL, Ollama y el worker automático:

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f worker
```

El primer inicio descarga aproximadamente 4.3 GB para Gemma 4. El worker importa correo IMAP y procesa análisis cada 15 minutos. También se puede ejecutar una sola vez desde el entorno virtual:

```powershell
python manage.py procesar_analisis_pendientes --limit 2
python manage.py automatizar_pipeline --once
```

Las rúbricas y criterios se administran desde Django Admin. Las rúbricas usadas quedan inmutables; para cambiar criterios debe crearse una versión nueva.

API autenticada: `/api/rubricas/`, `/api/analisis/`, `/api/documentos/{id}/analisis/` y `POST /api/documentos/{id}/analizar/`.

## Vacantes conversacionales

La fase 4 permite definir una vacante por mensajes, confirmar una rúbrica y ejecutar un ranking histórico de todos los currículums disponibles.

Flujo de API autenticada:

1. `POST /api/vacantes/` con `{ "mensaje": "..." }` crea la conversación y devuelve `202`.
2. `GET /api/vacantes/{id}/mensajes/` consulta la propuesta del agente cuando el worker termina.
3. `POST /api/vacantes/{id}/mensajes/` agrega aclaraciones antes de confirmar.
4. `POST /api/vacantes/{id}/confirmar/` congela la rúbrica propuesta.
5. `POST /api/vacantes/{id}/evaluar/` crea una ejecución asíncrona sobre los CV disponibles.
6. `GET /api/vacantes/{id}/ejecuciones/{ejecucion_id}/ranking/` devuelve diez candidatos por página, evidencia y enlaces protegidos a sus PDF.

Si una ejecución termina parcial, `POST /api/vacantes/{id}/ejecuciones/{ejecucion_id}/reintentar/` reencola únicamente los candidatos con error.

Los requisitos obligatorios faltantes se señalan, pero ningún candidato se rechaza automáticamente. Para incorporar CV nuevos se crea manualmente otra ejecución, conservando el historial anterior.

## Interfaz web

Con Django ejecutándose, abra `http://127.0.0.1:8000/` e inicie sesión con un usuario de Django. La interfaz permite crear vacantes conversacionales, confirmar criterios, consultar progreso, reintentar errores y revisar el ranking con evidencia y enlaces protegidos a los PDF.
