# Desplegar en Render con Firebase y Claude Haiku

La arquitectura actual es **Render + Cloud Firestore + Firebase Storage + Claude Haiku**. Render no almacena bases de datos ni necesita un disco persistente para esta versión.

## Preparación en Firebase y Anthropic

Sigue [FIREBASE.md](FIREBASE.md) para crear Firestore y el bucket, aplicar las reglas/índices y preparar la cuenta de servicio. Crea una API key de Anthropic con crédito y acceso al modelo Haiku configurado. No pongas secretos en GitHub ni en el chat.

## Despliegue

1. En [Render Dashboard](https://dashboard.render.com/) elige **New → Blueprint**.
2. Conecta el repositorio **Jontalas/DM**, rama **main**. El archivo `render.yaml` configura el servicio `dm-cronicas`.
3. Render pedirá los valores marcados `sync: false`: `FIREBASE_PROJECT_ID`, `FIREBASE_SERVICE_ACCOUNT_JSON`, `FIREBASE_STORAGE_BUCKET` y `ANTHROPIC_API_KEY`.
4. Revisa el plan de cómputo `0.5c-512mb`, la región Frankfurt y una instancia. Esta configuración de Render es de pago; no se ha contratado ningún servicio desde esta sesión. Firebase/Storage y Anthropic tienen sus propios requisitos de facturación, explicados en [FIREBASE.md](FIREBASE.md).
5. Crea el servicio y abre la URL HTTPS asignada cuando aparezca Live.

También puedes configurar un Web Service manualmente con estos valores:

| Opción | Valor |
|---|---|
| Runtime | Python 3.13, según `.python-version` |
| Build | `pip install -r requirements.txt` |
| Arranque | `python serve.py` |
| Salud | `/healthz` |
| Dirección | `0.0.0.0`; el puerto se toma de `PORT` |
| Servidor | Waitress, un proceso y 16 hilos |
| Disco persistente | No necesario |
| Modelo | `ANTHROPIC_MODEL=claude-haiku-5-5` |

Las credenciales de Firebase también pueden entregarse como archivo secreto: configura `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/firebase-service-account.json` y elimina `FIREBASE_SERVICE_ACCOUNT_JSON`. El SDK usa ese archivo mediante Application Default Credentials. El proyecto debe seguir en `FIREBASE_PROJECT_ID`.

Los secretos no se incluyen en las respuestas del servidor. Si Firebase falta o no responde, el servicio falla al iniciar o devuelve error; no crea una base local para aparentar persistencia. `/healthz` comprueba una lectura a Firestore y devuelve 503 si falla. No prueba la disponibilidad de Claude ni de los libros; `/api/status` muestra por separado el modelo configurado y las páginas indexadas.

## Manuales y campañas

Carga los originales y sus índices desde tu ordenador con `python scripts/firebase_books.py`, siguiendo [FIREBASE.md](FIREBASE.md). No necesitas transferirlos a la máquina de Render, ni instalar OCR allí. Los documentos no están incluidos en el repositorio.

Las salas nuevas se guardan directamente en Firestore. Si tienes campañas SQLite anteriores, expórtalas con `scripts/export_sqlite_campaigns.py` e impórtalas desde el diario de una sala nueva. La aplicación no migra datos silenciosamente durante un despliegue.

Si ya habías creado el despliegue anterior con disco, conserva el disco y sus copias hasta verificar la migración. Este cambio no borra sus datos. Revisa el estado del recurso en Render antes de retirar el disco antiguo y dejar de pagarlo; el código nuevo no lo utiliza.

## Comprobación después de desplegar

1. Abre `/healthz`: debe responder `{"status":"ok"}`.
2. Abre `/api/status`: debe indicar Firebase, Haiku y las páginas importadas (577/329/102).
3. Crea una campaña/personaje y envía una intervención con IA. Esta será una llamada real a Anthropic.
4. Abre una invitación desde otro navegador y comprueba identidad y estado compartido.
5. Reinicia el servicio en Render y verifica que la campaña sigue disponible: el estado vive en Firestore.
6. Abre una referencia de un manual para comprobar permisos del bucket y transmisión del PDF.

Se mantiene una sola instancia para conservar el orden local de generación. Firestore valida las versiones y la deduplicación de forma transaccional. Escalar más instancias requeriría gestionar también los trabajos de IA entre procesos; no se presenta como una capacidad ya completa.

La sincronización actual consulta el servidor cada 2,5 segundos y produce lecturas a Firebase, aunque una versión sin cambios evita descargar otra vez la instantánea. Configura seguimiento del consumo en tus cuentas. La arquitectura no elimina las limitaciones de reglas descritas en [README.md](README.md).

El código y el emulador están probados localmente. No se ha creado ni validado un despliegue real en tu cuenta de Render/Firebase/Anthropic durante esta sesión.
