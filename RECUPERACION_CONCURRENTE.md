# Recuperación de tiradas con intervenciones intermedias

Desplegado: 03c2b2b0013d295f3f8c9d34486194bde276839f, Render 7587669049 success, revisión/salud exactas. Ensayo aislado de producción sin IA: ámbito nuevo, dados de servidor [4,2], fallo correctamente conservado, duplicado/copia válidos, sin continuación narrativa. Fallos de commit/OOC/cliente nuevo probados en emulador, no inyectados en producción. Las referencias inferiores a «pendiente/no integrado» son la secuencia de construcción previa.

## Integración local posterior, 6 de noviembre

Solicitudes nuevas llevan randomnessScope:pending-resolution-v2. Las antiguas siguen usando actionId/version, sin reinterpretar semillas ya reservadas. El servidor deriva clave/huella de solicitud, propietario, paquete, elecciones, fichas y registros de mundo; el estado completo vuelve a pasar su preflight antes de cualquier dado. ActionRandomness acepta explícitamente ese descriptor. Firestore confirma su clave en el mismo lote que estado y marcador HTTP; la versión/CAS general de la mesa permanece obligatoria.

La recuperación del navegador intenta primero el envío original. Solo ante 409 y la misma solicitud pendiente con el ámbito nuevo, carga el estado vigente y envía una vez las mismas decisiones con id/versión HTTP nuevos. Persiste ese cuerpo antes de enviarlo; si vuelve a interrumpirse puede recuperarlo sin repetir consecuencias. No añade llamadas a IA ni cambios por consultar.

Coste específico: cuando una resolución nueva no genera dados del servidor, una lectura de la reserva comprueba que no está sustituyendo una secuencia ya reservada por dados físicos o una rama sin dados. No crea semillas ni escrituras para ello. Las resoluciones que sí generan dados reutilizan la reserva normal, sin esa lectura adicional. Se conserva así la consistencia entre reintentos; no afecta a navegación ni a las solicitudes antiguas.

Validaciones locales: descriptor/HMAC, lote Firestore/CAS/cliente nuevo y rechazo de claves inválidas correctos. HTTP/Waitress: fallo de commit, OOC de otro jugador, cuerpo antiguo rechazado, cambio a dados físicos rechazado, cliente nuevo y nuevo id/versión recuperan [5,6], ambas fichas/objetivo/revelación y duplicado sin IA. Navegador de recuperación automático y regresión de plan-3 correctos. Suite completa en ejecución, `.deps/pending-recovery-final-tests.log`, sesión 61059. No desplegado todavía.

Validación final local: **518 pruebas completas con emulador correctas sin omisiones (221,200 s)**. Captura original antigua revalidada sin IA; no se han repetido evaluaciones narrativas ni alterado sus resultados negativos. Pendiente respaldo/despliegue y verificación de producción en este punto.

Estado: análisis del siguiente bloque, sin cambio de comportamiento. La recuperación actual está comprobada cuando falla el commit y la versión de la mesa sigue igual: semilla privada duradera, cliente Firestore nuevo, dos fichas/objetivo/revelación y barrera conjunta. No vuelve a llamar al proveedor ni genera otra secuencia.

Primer bloque aislado posterior: pending_randomness.py describe clave/huella/versión de reserva por solicitud con opt-in pending-resolution-v2. Cinco pruebas correctas: legado intacto, mensaje OOC/id/versión HTTP no cambian la reserva; cambios de fichas/mundo/elecciones sí cambian su huella; propietario/solicitud/ámbito inválidos rechazados. Solo devuelve hashes, sin fichas. No integrado al almacenamiento, servidor ni navegador; todavía no recupera resoluciones con versiones intermedias.

El servidor calcula fingerprint sobre el cuerpo entero, incluido version. Antes de ejecutar compara esa versión con la mesa actual. La reserva de ActionRandomness se identifica por campaign/actionId y vincula actor, fingerprint y version. Si otra intervención avanza la mesa tras una interrupción, el cuerpo original se rechaza por versión. Cambiar version cambia la huella; reutilizar el identificador no sustituye la reserva. Es una negativa conservadora, no una recuperación automática ya implementada.

Siguiente objetivo: permitir recuperar la misma solicitud mecánica pendiente cuando la intervención intermedia no alteró su legalidad, sin permitir otra secuencia de dados ni aplicar un resultado sobre fichas distintas. Mantener el control de versiones para todas las demás acciones; no eliminarlo de forma general.

Una solución deberá identificar la resolución por solicitud pendiente/propietario/paquete/elecciones normalizadas/revisiones de ambas fichas. Examinar también visibilidad, contexto de escena, descubrimientos y vínculos de objetivos: una revisión de ficha idéntica por sí sola no acredita que el mundo no haya cambiado. Validar todo antes de usar la reserva. Un nuevo mensaje OOC puede ser compatible; retirar la solicitud, cambiar objetivo o contexto, sustituir paquete o confirmar otra resolución debe impedir reutilizarla.

La reserva semántica y su barrera de confirmación requieren ampliar explícitamente el contrato del almacenamiento. Hoy commit confirma la reserva identificada por actionId; no basta con cambiar la clave de aleatoriedad en memoria. No introducir una segunda escritura posterior que deje fichas confirmadas y reserva reutilizable. Conservar compatibilidad y recuperación de las reservas anteriores.

Pruebas pendientes: interrupción antes de commit seguida de OOC de otro jugador, cliente nuevo y nuevo cuerpo con versión vigente; secuencia original intacta. CAS simultáneo debe permitir una sola confirmación. Cambios de entradas, objetivo, revisión, contexto o propietario deben rechazarse antes de dados; solicitud retirada/confirmada tampoco puede recuperarse. La comparación de resultados necesita usar el HMAC real de una semilla controlada: sustituir hmac.digest solo en el primer intento produciría artificialmente otra secuencia en el reintento y no comprobaría la persistencia.

No añadir IA, consultas periódicas ni una lectura por herramienta local. Reutilizar datos cargados y reservar almacenamiento solo cuando haya que generar dados del servidor. No trasladar al jugador la elección de qué consecuencia antigua volver a aplicar.
