# Preparación de aventura importable

## PNJ preparados en el mismo archivo (formato 2, validación local)

Validación integrada: 489 pruebas completas con emulador correctas sin omisiones (210,018 s), HTTP/Waitress de inicio/resolución/copia, navegador plan-2 y regresión plan-1 correctos. Pendiente despliegue y evaluación narrativa real de este bloque.

`cronicas-adventure-plan-2` conserva fuente, paquete, objetivos y descubrimientos del formato 1 y añade `npcPreparation`. Ese objeto usa `cronicas-adventure-actors-1`, con paquete exacto, `npcs` (descripciones completas de ficción) y `actors` (id de 24 caracteres hexadecimales, npc, profile, stages y publicFields). Ejemplo propio CC0: test_fixtures/original-adventure-actor-plan.json. No contiene reglas Pathfinder.

Cada actor exige un perfil existente del paquete, todas sus etapas y sus elecciones. No acepta estadísticas directas, otra versión del paquete, identidades repetidas, un PJ como actor ni PNJ inexistentes. Los dados de preparación, si el perfil los exige, deben estar expresamente aportados y se reproducen sin volver a tirar; los perfiles sin dados no generan aleatoriedad. El módulo no inventa estadísticas a partir del nombre de una criatura. Aplican los límites de dieciséis actores, 200.000 bytes de registro y 60.000 bytes de archivo completo. La confirmación de uso de la preparación aportada cubre los perfiles del archivo; sigue siendo contenido aportado, sin certificación automática de su fidelidad reglamentaria.

El servidor compila y verifica antes de la llamada de apertura. El contrato optativo `rule-pack-director-plan-actors-start-6` entrega al director los PNJ preparados y sus notas de ficción; no sus fichas. La confirmación de apertura instala también las fichas privadas y su posición real de origen en el registro. No hay otra llamada de IA ni una acción de configuración por PNJ. Las opciones de objetivo aparecen por el contexto abstracto realmente acreditado y los permisos del jugador. Importar y recuperar reproduce creaciones y acciones sin dados nuevos.

Plan-1 conserva el contexto anterior. Los vínculos de objetivos/descubrimientos sobre un PNJ concreto siguen pendientes: una resolución dirigida no los completa. La dirección narrativa real de los contratos nuevos todavía no está aceptada; las pruebas actuales usan proveedor simulado. El preparador de cualquier PDF y la generación automática de perfiles desde prosa no se incluyen.

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
