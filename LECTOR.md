# Reglamentos: lectura por páginas

La pestaña Reglamentos descarga únicamente la página elegida, como imagen WebP. No abre el PDF completo ni precarga otras páginas. Anterior, siguiente, número de página, referencias y marcadores comparten este visor. Incluye zoom y una vista de lectura ampliada. Las referencias conservan la numeración de página del archivo PDF.

Las páginas se preparan localmente una sola vez desde los originales: 1.400 píxeles de ancho, WebP con calidad 80. No interviene la IA. Los originales permanecen privados y sin modificaciones. La búsqueda utiliza el índice de texto existente en Firestore; el visor gráfico no permite seleccionar texto como un PDF ni proporciona OCR adicional.

Medición de los tres manuales actuales: TREY, 102 páginas y 18.069.248 bytes (177 KB por página de media); reglas, 577 páginas y 185.362.534 bytes (321 KB); bestiario, 329 páginas y 109.613.392 bytes (333 KB). Son 313.045.174 bytes de derivados privados en total. La página mayor ocupa 469.908 bytes. Se carga solo la elegida, aunque todas estén preparadas en Storage.

## Cachés y coste

- Navegador: IndexedDB y memoria, hasta 50 páginas o 32 MiB en cada caché. Se reutilizan después de recargar; si IndexedDB no está disponible, funciona la memoria durante la sesión. Las claves incluyen una huella de la credencial, el libro y su versión. Volver al inicio con «Salir» vacía esta caché. El navegador también puede expulsarla por falta de espacio.
- Servidor: caché compartida en memoria de 32 MiB; páginas durante una hora y metadatos durante 60 segundos. Las descargas simultáneas del mismo objeto se agrupan. Se comprueba la autenticación antes de servir cualquier página, incluso una respuesta 304. Reiniciar Render pierde esta caché temporal.
- Una página nueva genera una petición al servidor y, si falta en su caché, una descarga privada de Storage. No consulta Firestore ni llama a Claude para leerla, aparte de la autenticación habitual. Los metadatos de versión también se descargan de Storage cuando caducan.
- No hay disco persistente ni servicio nuevo. Se añade a Storage una copia comprimida por páginas de cada manual, con su correspondiente coste de almacenamiento; evita transferir PDFs completos de decenas o cientos de MB por consulta.

## Preparación y actualización

Con las credenciales y variables de [FIREBASE.md](FIREBASE.md), ejecutar localmente:

```powershell
python -m pip install -r requirements-extract.txt
python scripts/prepare_book_pages.py --books-dir "$env:USERPROFILE\Desktop" --upload
```

No se ejecuta durante el arranque de Render. Los archivos generados quedan en `.deps/book-pages`, fuera de Git. La huella del original y los parámetros de conversión determinan la versión. Repetir una versión publicada evita nuevas cargas; una carga interrumpida conserva las páginas terminadas y se puede reanudar. El manifiesto activo solo cambia cuando todas las páginas de ese libro están subidas. Una actualización de manifiesto puede tardar hasta dos minutos en atravesar las cachés de metadatos de servidor y navegador; recargar elimina la del navegador.

Las versiones anteriores en Storage no se eliminan automáticamente: antes de publicar una sustitución se debe identificar la versión activa, comprobar la nueva y retirar únicamente los derivados obsoletos. Nunca borrar originales ni índices. Los PDFs originales conservan su ruta privada heredada por compatibilidad; el visor normal no la utiliza.

## Verificación

`python -m unittest test_reader test_server test_render` cubre límites, caducidad, concurrencia, versiones, formatos, errores de descarga, publicación incompleta y autenticación/ETag bajo HTTP y Waitress. `node test_reader_browser.cjs` utiliza páginas sintéticas y prueba descargas individuales, reutilización tras recargar, navegación, zoom, ampliación, cancelación, recuperación y móvil, sin acceder a servicios de pago.
