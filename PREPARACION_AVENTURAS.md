# Preparación de aventura importable

Despliegue confirmado: `2a6d396cc07031aea96b1a4fd46bf73a1e371a8d`, Render 7578159048 success y salud/revisión exactas. Ensayo aislado de producción sin IA: paquete incompatible rechazado antes de apertura; compilación/apertura/solicitud simuladas importadas explícitamente, resolución real, revelación, copia/propietario/invitado, duplicados y CRLF correctos. Navegador producción anfitrión/copia/invitado/móvil correcto, sin acciones al consultar. La compilación y apertura por API se prueban con proveedor simulado en HTTP/Waitress; todavía no hay aceptación real de dirección narrativa para este contrato.

Formato optativo `cronicas-adventure-plan-1`, implementado y validado localmente, pendiente de despliegue en este punto. El archivo de ejemplo `test_fixtures/original-adventure-plan.json` contiene ficción y reglas de ejemplo propias; no implementa Pathfinder ni otro manual. Validación: 438 pruebas completas con emulador sin omisiones, correctas (154,456 s); 101 afectadas anteriores correctas. Navegadores de aventura anterior y preparación importable correctos con proveedor simulado; edición incompatible no envía acciones, borrador retenido, original CRLF exacto, objetivos/catálogo listos al iniciar, resolución física y una continuación automática. No se han efectuado inferencias reales nuevas para este bloque.

El jugador puede seleccionar una preparación `.json` en el mismo apartado de aventura aportada que acepta `.txt` y `.md`. Confirma el permiso de uso habitual e inicia: objetivos y descubrimientos quedan listos en esa misma confirmación, sin una segunda configuración técnica. No añade llamadas de IA: la apertura utiliza su llamada normal; la compilación, validación y revelaciones se calculan por código. Navegar, cargar el archivo y editar el borrador son operaciones locales.

El archivo contiene:

- `format`: `cronicas-adventure-plan-1`.
- `package`: identidad, versión y SHA-256 exactos del paquete de reglas compatible.
- `source`: título y texto original de aventura, hasta 12.000 caracteres.
- `objectives`: descripciones con id, title, detail, known y private, hasta doce.
- `discoveries`: citas exactas con id, objective, field, start, end y text, hasta doce.

La preparación está limitada a 60.000 bytes serializados. Una consecuencia necesita un objetivo conocido de esa preparación y un booleano almacenado que una acción jugable calcule de forma incondicional. Posiciones start/end son caracteres Unicode del texto original, conservando CRLF; no son bytes. No se aceptan recompensas, daño, viajes, efectos sobre otras fichas ni fórmulas nuevas en este formato.

El servidor comprueba paquete, fuentes y citas antes de llamar al director. La narración conoce los objetivos preparados como oportunidades, sin convertirlos en decisiones del personaje ni hechos ocurridos. Sus actualizaciones no pueden cambiar retrospectivamente títulos/detalles. Descubrimientos solo pasan al diario al confirmar la solicitud vinculada con el resultado requerido; la fuente y el catálogo restantes siguen privados. Exportar/copy reproduce originales de texto y definiciones compiladas, no el formato de espacios del JSON importado. `planSha256` identifica el documento semántico inicial; no autentica por sí solo un archivo externo ni sustituye la validación de evidencias.

La pertinencia entre una cita y su objetivo sigue siendo preparación aportada: coincidencia exacta no certifica interpretación semántica de la aventura. No hay todavía conversión automática desde cualquier PDF, texto o manual, ni asistente completo de autoría. La preparación técnica por API anterior continúa para compatibilidad. No se anuncia aventura autónoma completa ni hito de prueba personal por este recorrido.
