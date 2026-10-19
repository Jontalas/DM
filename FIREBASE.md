# Firebase y Claude Haiku

Esta es la configuración vigente. Las partidas y los índices se guardan en **Cloud Firestore**; los PDF originales en **Firebase Storage**; el director usa la **API Messages de Anthropic con Claude Haiku**. Render aloja el servidor y la interfaz. No hay una base SQLite activa ni un proveedor Ollama alternativo.

## Crear el proyecto y dar acceso al servidor

1. En [Firebase Console](https://console.firebase.google.com/), crea o selecciona tu proyecto.
2. Activa **Cloud Firestore**, edición Standard, modo nativo y base `(default)`. Elige la ubicación apropiada; no se configura una base Realtime Database.
3. Activa **Storage** y copia el nombre exacto del bucket. Los nuevos suelen llamarse `PROYECTO.firebasestorage.app`; los existentes pueden usar `PROYECTO.appspot.com`. No añadas `gs://` a la variable.
4. Crea una cuenta de servicio para el servidor con acceso de lectura/escritura a Firestore y lectura de los objetos de Storage. Roles habituales: **Cloud Datastore User** y **Storage Object Viewer** sobre el bucket. La herramienta que sube manuales necesita además crear/sustituir objetos: usa una cuenta administrativa separada o permisos **Storage Object Admin** para esa operación.
5. Proporciona las credenciales al servidor con **una** de estas opciones: `FIREBASE_SERVICE_ACCOUNT_JSON` con el JSON completo como secreto; o un archivo secreto y `GOOGLE_APPLICATION_CREDENTIALS` apuntando a su ruta. La configuración pública de una aplicación web Firebase (`apiKey`, `authDomain`, etc.) no sustituye estas credenciales de servidor.

No pegues claves privadas en el chat ni en archivos versionados. La plantilla `.env.example` solo muestra nombres; la aplicación no carga archivos `.env` automáticamente. [Credenciales del servidor](https://firebase.google.com/docs/admin/setup).

**Firebase Storage requiere el plan Blaze con facturación habilitada**, aunque dispone de cuotas sin coste. No se ha activado ni contratado ningún plan en esta sesión. [Requisitos oficiales](https://firebase.google.com/docs/storage/faqs-storage-changes-announced-sept-2024).

## Reglas e índices

Se incluyen `firebase.json`, `firestore.rules`, `storage.rules` y `firestore.indexes.json`. Las reglas deniegan acceso directo desde el navegador; los SDK de servidor acceden mediante IAM. Los participantes siguen entrando con las invitaciones y credenciales de sesión de la mesa. **No se ha añadido Firebase Authentication**: no confundas guardar sesiones en Firestore con tener inicio de sesión por correo o Google.

Desde una terminal con la CLI de Firebase y acceso administrativo a tu proyecto:

```sh
npx firebase-tools login
npx firebase-tools deploy --project TU_PROYECTO --only firestore:rules,firestore:indexes,storage
```

Estas reglas son para un proyecto/bucket de esta aplicación. Revisa su integración si compartes Firebase con otras aplicaciones: la regla global deniega también el acceso directo de esos clientes. El servidor sigue filtrando secretos, notas y propietarios. Los índices excluyen el texto completo de cada página y los fragmentos binarios de las instantáneas; la búsqueda usa el campo de términos `tokens`.

## Variables

| Variable | Uso |
|---|---|
| `FIREBASE_PROJECT_ID` | Identificador del proyecto |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | JSON secreto completo de la cuenta de servicio |
| `GOOGLE_APPLICATION_CREDENTIALS` | Alternativa: ruta al archivo secreto |
| `FIREBASE_STORAGE_BUCKET` | Nombre del bucket, sin `gs://` |
| `FIREBASE_COLLECTION_PREFIX` | Opcional, `cronicas` por defecto |
| `ANTHROPIC_API_KEY` | Clave privada de Anthropic con crédito y acceso al modelo |
| `ANTHROPIC_MODEL` | `claude-haiku-5-5` por defecto; configurable dentro de la familia Haiku |

El identificador predeterminado se verificó en la [documentación oficial de modelos](https://platform.claude.com/docs/en/models/overview). Se usa `POST https://api.anthropic.com/v1/messages`, versión `2023-06-01`, con `output_config.format` y un esquema JSON de narración/propuestas. [Salida estructurada](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

La API key nunca se envía al navegador. Los secretos del director y las notas privadas no se incluyen en las solicitudes a Claude. Se recuperan hasta cinco páginas relevantes y una ventana de historial público; los tres libros completos no se envían en cada turno. Las respuestas truncadas, inválidas o rechazadas no confirman cambios de campaña.

Un nombre de modelo configurado y una clave presente no prueban acceso real ni calidad narrativa. No se ha hecho una llamada facturable con credenciales reales en esta sesión. Debes comprobar cuota, permisos y una escena de prueba después de configurar los secretos.

## Instalar los manuales

Con los PDF originales en tu Escritorio y los JSON de páginas en `data/`, configura las variables Firebase en tu terminal y ejecuta:

```powershell
python -m pip install -r requirements.txt
$env:FIREBASE_PROJECT_ID = 'tu-proyecto'
$env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\ruta\privada\firebase-service-account.json'
$env:FIREBASE_STORAGE_BUCKET = 'tu-proyecto.firebasestorage.app'
python scripts/firebase_books.py --books-dir "$env:USERPROFILE\Desktop" --index-dir data
```

Si aún no tienes los JSON, instala las dependencias de extracción y ejecuta `python extract_fast.py`:

```powershell
python -m pip install --target .deps -r requirements-extract.txt
python extract_fast.py
```

El script valida los archivos locales, sube cada PDF privado a `manuals/CLAVE/original.pdf` y escribe las páginas/términos en Firestore. El índice se activa solo después de escribir todas sus páginas. Puedes seleccionar `--book trey`, `--book reglas` o `--book bestiario`; sin selección carga los tres. Comprueba después en `/api/status` **577 páginas de reglas, 329 de bestiario y 102 de TREY**.

Los libros se sirven a través del backend tras validar la sesión; no se crean enlaces públicos permanentes. En desarrollo se permite leer originales del Escritorio si no has configurado un bucket; las campañas y las búsquedas siguen requiriendo Firestore. En Render los PDF se leen siempre de Firebase Storage.

Los PDF y sus JSON no se suben a GitHub. `scripts/render_assets.py` se conserva como herramienta opcional de empaquetado/transporte privado de archivos locales; no instala nada en la base de datos. Para publicar los documentos se usa `scripts/firebase_books.py`.

## Persistencia y orden de acciones

Colecciones con el prefijo configurado:

- `cronicas_campaigns`: título, invitación, versión y referencia a la instantánea. Subcolecciones `members`, `actions` y `snapshots`.
- `cronicas_sessions`: sesión y jugador; el ID es SHA-256 de la credencial, no la credencial original.
- `cronicas_invites`: búsqueda por SHA-256 de la invitación.
- `cronicas_manuals`: índice activo y número de páginas; subcolección de índices y páginas.

El estado se comprime y divide en fragmentos de hasta **192 KiB**, evitando el límite de 1 MiB por documento de Firestore. El límite operativo actual es **16 MiB de JSON sin comprimir por campaña**, distinto del límite de Firestore. Los imports HTTP admiten hasta 8 MB. [Límites de Firestore](https://firebase.google.com/docs/firestore/quotas).

Un lote atómico confirma conjuntamente la nueva referencia de estado, el incremento de versión y el marcador de acción. La escritura exige que el documento de campaña conserve la fecha exacta de actualización leída, además de validar la versión. Las instantáneas son inmutables, por lo que leer varias piezas no mezcla estados de versiones diferentes. Un conflicto de confirmación no vuelve a tirar dados ni llamar al modelo. Repetir una acción ya confirmada devuelve `duplicate` sin aplicarla ni solicitar otra narración. Este mecanismo evita bloqueos de lectura y reintentos de transacciones durante la confirmación; las altas por invitación siguen usando su transacción.

La llamada a Claude y los dados ocurren antes de la transacción; un conflicto descarta el resultado candidato. Una caída después de consumir la API y antes de confirmar puede requerir otra inferencia al reintentar, aunque el estado del juego solo se confirma una vez. No se promete facturación de inferencia exactamente una vez ante caídas.

La sincronización consulta cada **15 segundos con la pestaña visible**, se pausa al ocultarla y se actualiza al volver. Los cambios propios se actualizan inmediatamente; los de otros jugadores pueden tardar hasta 15 segundos. Una versión coincidente devuelve «sin cambios». No se ha sustituido por listeners Firebase en el navegador. Las comprobaciones de salud reutilizan durante 60 segundos el último acceso correcto a Firestore, por lo que un fallo remoto puede tardar ese tiempo en detectarse. Las lecturas, escrituras, almacenamiento y transferencia pueden facturarse: vigila uso y presupuesto. [Facturación de Firestore](https://firebase.google.com/docs/firestore/pricing).

## Migrar campañas anteriores y conservar copias

No se borran ni modifican tus bases SQLite locales. Para migrarlas sin ejecutar la aplicación antigua:

```powershell
python scripts/export_sqlite_campaigns.py data/campaigns.sqlite campaign-exports
```

La utilidad abre la base antigua en modo de solo lectura y genera un JSON por campaña. Crea una sala en la nueva aplicación, entra como anfitrión e importa el JSON desde el diario. Los personajes se reasignan al anfitrión importador y se descartan las notas privadas del campo `private`, como en la importación anterior. Las credenciales e invitaciones antiguas no se trasladan; distribuye nuevas invitaciones. Cada importación lleva versión e identificador para impedir duplicarla por reconexión.

Para copias por campaña, utiliza Exportar en el diario. Para una copia administrativa completa, configura [backups/exportación administrados de Firestore](https://firebase.google.com/docs/firestore/manage-data/export-import) y copias/versiones del bucket de Storage desde tu cuenta. La antigua herramienta `backup_db.py` de SQLite se ha retirado.

Las instantáneas anteriores se conservan inicialmente. Para revisar fragmentos sin referencia de más de siete días:

```sh
python scripts/firebase_cleanup.py
# Solo después de revisar: elimina los candidatos, preservando la instantánea activa.
python scripts/firebase_cleanup.py --days 7 --apply
```

El primer comando es una simulación. La revisión recorre los fragmentos de esta aplicación y también genera lecturas facturables; no es una política de backup ni se ejecuta automáticamente. Los índices antiguos de manuales se conservan al reimportar.

## Pruebas sin credenciales reales

```sh
python -m pip install -r requirements.txt
python -m unittest test_engine test_server test_render test_firebase test_migration -v
```

Sin emulador, las pruebas HTTP usan un doble explícito en `test_support.py`; las pruebas específicas del emulador se omiten. Ese doble no forma parte del servidor ni sirve como almacenamiento de producción.

Para probar el controlador real, instala Node y Java 21 y ejecuta en una terminal:

```sh
npx firebase-tools emulators:start --project demo-cronicas-tests --only firestore
```

En otra terminal PowerShell:

```powershell
$env:FIRESTORE_EMULATOR_HOST = '127.0.0.1:8080'
$env:FIREBASE_PROJECT_ID = 'demo-cronicas-tests'
python -m unittest test_engine test_server test_render test_firebase test_migration -v
```

Con esas variables las pruebas HTTP y las de persistencia usan el SDK real contra el emulador oficial, en colecciones de prueba con prefijo aleatorio. No se utiliza un proyecto real. Nunca configures `FIRESTORE_EMULATOR_HOST` en Render: el arranque lo rechaza.

Se han verificado concurrencia entre clientes, deduplicación, recuperación desde un cliente nuevo y estados mayores de 1 MB, además del motor, permisos y transporte HTTP. Los tests del proveedor inspeccionan la solicitud y usan respuestas de prueba; no certifican el comportamiento de una IA real. La carga/lectura contra un bucket real y el despliegue final necesitan las credenciales de tu cuenta.
