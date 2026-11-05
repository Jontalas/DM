# Recuperación de tiradas con intervenciones intermedias

Estado: análisis del siguiente bloque, sin cambio de comportamiento. La recuperación actual está comprobada cuando falla el commit y la versión de la mesa sigue igual: semilla privada duradera, cliente Firestore nuevo, dos fichas/objetivo/revelación y barrera conjunta. No vuelve a llamar al proveedor ni genera otra secuencia.

El servidor calcula fingerprint sobre el cuerpo entero, incluido version. Antes de ejecutar compara esa versión con la mesa actual. La reserva de ActionRandomness se identifica por campaign/actionId y vincula actor, fingerprint y version. Si otra intervención avanza la mesa tras una interrupción, el cuerpo original se rechaza por versión. Cambiar version cambia la huella; reutilizar el identificador no sustituye la reserva. Es una negativa conservadora, no una recuperación automática ya implementada.

Siguiente objetivo: permitir recuperar la misma solicitud mecánica pendiente cuando la intervención intermedia no alteró su legalidad, sin permitir otra secuencia de dados ni aplicar un resultado sobre fichas distintas. Mantener el control de versiones para todas las demás acciones; no eliminarlo de forma general.

Una solución deberá identificar la resolución por solicitud pendiente/propietario/paquete/elecciones normalizadas/revisiones de ambas fichas. Examinar también visibilidad, contexto de escena, descubrimientos y vínculos de objetivos: una revisión de ficha idéntica por sí sola no acredita que el mundo no haya cambiado. Validar todo antes de usar la reserva. Un nuevo mensaje OOC puede ser compatible; retirar la solicitud, cambiar objetivo o contexto, sustituir paquete o confirmar otra resolución debe impedir reutilizarla.

La reserva semántica y su barrera de confirmación requieren ampliar explícitamente el contrato del almacenamiento. Hoy commit confirma la reserva identificada por actionId; no basta con cambiar la clave de aleatoriedad en memoria. No introducir una segunda escritura posterior que deje fichas confirmadas y reserva reutilizable. Conservar compatibilidad y recuperación de las reservas anteriores.

Pruebas pendientes: interrupción antes de commit seguida de OOC de otro jugador, cliente nuevo y nuevo cuerpo con versión vigente; secuencia original intacta. CAS simultáneo debe permitir una sola confirmación. Cambios de entradas, objetivo, revisión, contexto o propietario deben rechazarse antes de dados; solicitud retirada/confirmada tampoco puede recuperarse. La comparación de resultados necesita usar el HMAC real de una semilla controlada: sustituir hmac.digest solo en el primer intento produciría artificialmente otra secuencia en el reintento y no comprobaría la persistencia.

No añadir IA, consultas periódicas ni una lectura por herramienta local. Reutilizar datos cargados y reservar almacenamiento solo cuando haya que generar dados del servidor. No trasladar al jugador la elección de qué consecuencia antigua volver a aplicar.
