# Alojar Crónicas en Render

El repositorio incluye `render.yaml`, `requirements.txt`, `.python-version` y un servidor WSGI con **Waitress**. El servidor de desarrollo `python server.py` sigue disponible para uso local; Render ejecuta **`python serve.py`**, con un único proceso y 16 hilos para mantener coherente el bloqueo del motor.

## 1. Crear el servicio

1. En [Render Dashboard](https://dashboard.render.com/), elige **New → Blueprint**.
2. Conecta GitHub y selecciona **Jontalas/DM**, rama **main**.
3. Render leerá el archivo `render.yaml`. Revisa el servicio `dm-cronicas`, la región Frankfurt, el plan `0.5c-512mb` y el disco de 1 GB antes de crear recursos.
4. Confirma la creación en Render y espera al estado Live. Abre la URL HTTPS que te asigne la plataforma.

**Esta configuración es de pago**: los discos persistentes no están disponibles en servicios web gratuitos. No se ha creado ningún servicio ni contratado ningún plan desde esta sesión. Puedes elegir otro plan compatible en Render. [Discos de Render](https://render.com/docs/disks), [referencia de Blueprint](https://render.com/docs/blueprint-spec).

Render detecta su puerto mediante `PORT`; el arranque escucha en `0.0.0.0`. La comprobación de salud es `GET /healthz`: devuelve 200 si SQLite responde y 503 si la consulta falla. No necesita manuales ni IA para estar saludable. `/api/status` informa por separado del modelo configurado y las páginas indexadas; configurar un nombre de modelo no prueba que el proveedor responda.

La base se inicializa al **arrancar**, nunca en el build: el disco persistente solo está disponible durante la ejecución del servicio. [Disponibilidad del disco](https://render.com/docs/disks#disk-limitations-and-considerations).

## 2. Configuración incluida

| Opción | Valor |
|---|---|
| Runtime | Python 3.13, último parche de esa serie según `.python-version` |
| Build command | `pip install -r requirements.txt` |
| Start command | `python serve.py` |
| Health check | `/healthz` |
| Instancias | 1 |
| Disco | `/var/data`, 1 GB |
| `DATA_DIR` | `/var/data/cronicas` |
| `INDEX_DIR` | `/var/data/cronicas/indexes` |
| `BOOKS_DIR` | `/var/data/cronicas/books` |
| `HOST` | `0.0.0.0` |

Campañas y búsquedas se guardan en `/var/data/cronicas/campaigns.sqlite`; los archivos WAL/SHM quedan al lado, en el mismo disco. `DATABASE_PATH` permite cambiar la ruta de SQLite si se necesita; debe seguir dentro del disco persistente. No la cambies para una instalación normal.

No elimines el disco ni cambies las rutas al actualizar. Los redeploys conservan sus archivos, pero tendrán una breve interrupción: Render no permite despliegues sin interrupción con este disco. No aumentes los procesos ni las instancias: el motor actual depende de un bloqueo compartido en memoria. [Limitaciones del disco](https://render.com/docs/disks#disk-limitations-and-considerations).

Para crear el servicio manualmente sin Blueprint, introduce las mismas opciones y añade el disco **antes de usarlo para partidas**. Arrancar en un sistema de archivos efímero permite ejecutar código, pero no garantiza conservar campañas tras un reinicio.

## 3. Instalar los tres manuales sin publicarlos en GitHub

Los PDF, sus textos extraídos y las partidas no forman parte del repositorio. Al primer despliegue la mesa arranca con **0 páginas indexadas**, hasta transferir los documentos.

En el ordenador que contiene los originales y los índices de `data/`, ejecuta:

```powershell
python scripts/render_assets.py pack render-assets.zip
```

Este paquete privado contiene solo los tres originales y sus tres JSON. No incluye SQLite, invitaciones, credenciales ni dependencias. El ZIP está ignorado por Git. Si faltan índices, genéralos primero con `python extract_fast.py`; para preparar otro equipo instala las dependencias de extracción con `python -m pip install --target .deps -r requirements-extract.txt`. El script de extracción original busca los PDF con sus nombres actuales en el Escritorio.

Transfiere el ZIP de forma privada al servicio. Una opción es **Magic Wormhole**, disponible en los runtimes nativos de Render: en tu ordenador instala `magic-wormhole` y ejecuta `wormhole send render-assets.zip`. En la pestaña **Shell** del servicio:

```sh
cd /var/data
wormhole receive
# Introduce el código de transferencia y acepta el archivo.
cd /opt/render/project/src
python scripts/render_assets.py install /var/data/render-assets.zip
```

También puedes usar SCP siguiendo las instrucciones específicas que muestra Render para tu servicio. [Transferir archivos al disco](https://render.com/docs/disks#transferring-files).

Después reinicia el servicio desde Render. El arranque indexará los fragmentos en SQLite. Confirma en `/api/status` que aparecen **577, 329 y 102 páginas**, y prueba abrir los libros desde la mesa. El instalador verifica las rutas permitidas y el formato básico del paquete; no hace OCR ni valida semánticamente las tablas. Sustituir índices de otros libros/ediciones en una base ya indexada necesita una migración adicional, no es una operación soportada por este instalador.

No subas el ZIP a un repositorio público. La transferencia e instalación de documentos debe hacerse en la Shell del servicio en ejecución, no durante el build.

## 4. Configurar la IA

El servicio de Render **no incluye Ollama ni un modelo**. Tampoco puede conectarse al `127.0.0.1` de tu ordenador. En **Environment**, añade:

```text
OLLAMA_URL=https://tu-servidor-ollama
OLLAMA_MODEL=identificador-exacto-del-modelo-instalado
OLLAMA_AUTH_TOKEN=token-del-proxy-si-lo-requiere
```

`OLLAMA_URL` es la dirección base, sin `/api/chat`. Se necesita un servidor remoto que exponga la API de Ollama por HTTPS, o un servicio accesible en la red privada de Render. El token opcional se envía como `Authorization: Bearer ...` y se mantiene en el servidor; no se incluye en el frontend, el repositorio ni el paquete de manuales.

No expongas tu Ollama doméstico sin controlar el acceso. No se ha contratado ni desplegado infraestructura de IA automáticamente. El plan de la mesa está dimensionado para la aplicación, no para alojar un modelo grande. Reinicia después de cambiar las variables y prueba una intervención real; la disponibilidad y calidad del modelo todavía deben verificarse en ese entorno.

Sin IA puedes preparar la campaña, consultar libros y usar el motor con «Responder con IA» desmarcado. La aplicación no inventa respuestas prefijadas para aparentar que hay un director conectado.

## 5. Copias y traslado de campañas

- Exporta cada campaña desde su diario para una copia funcional de sus datos.
- Para copiar la base completa, incluida la información de reconexión, en la Shell ejecuta:

```sh
python scripts/backup_db.py /var/data/cronicas/backups/campaigns-copia.sqlite
```

Usa un nombre nuevo para cada copia. El script usa la API de backup de SQLite para incluir cambios confirmados que todavía estén en el WAL. Descarga una copia fuera de Render mediante transferencia privada; una copia que solo está en el mismo disco no protege frente a su eliminación. No copies únicamente `campaigns.sqlite` mientras la aplicación escribe.

Puedes trasladar las campañas locales exportando/importando JSON con la interfaz. La importación reasigna personajes al anfitrión actual y descarta las notas privadas anteriores, como indica el README. Las sesiones del navegador son específicas del dominio: visitar la nueva URL no recupera por sí solo el token de localhost.

## 6. Comprobaciones

Se prueban el mismo motor y las mismas rutas JSON tanto bajo el servidor local como bajo Waitress: identidad, permisos, persistencia, deduplicación, origen HTTPS detrás del proxy, archivos estáticos, `HEAD`, salud y acceso autenticado a libros. También se comprueba el paquete de documentos con datos de prueba y la copia SQLite.

```sh
pip install -r requirements.txt
python -m unittest test_engine test_server test_render -v
```

Las pruebas usan textos/PDF ficticios identificados como fixtures; no requieren distribuir los manuales en Git. No sustituyen una prueba real desplegada en Render ni una conversación con un modelo real. Tras publicar, comprueba salud, crea una campaña, invita desde otro navegador, reinicia y verifica que el estado se conserva. Las limitaciones de reglas y de IA enumeradas en [README.md](README.md) siguen vigentes.
