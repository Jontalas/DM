# Actores reglamentarios y objetivos de acciones

Siguiente capacidad general pendiente. Este contrato no anuncia combate genérico ni reemplaza las reglas verificadas del módulo Pathfinder. La prueba inicial usará ficción y reglas propias; trasladar una mecánica de un manual exige consultar sus originales y registrar edición/páginas.

Registro desplegado en 7c2bc109f4548a5ce86553b0fabebb9be6264607, Render 7578772032 success, salud/revisión exactas. Ensayo técnico real de producción con apertura simulada y cero inferencias: primer actor creado con dado del servidor [5], segundo actor oculto con dado aportado; duplicados, registro privado, campos públicos, copia/controlador e invitado correctos. Navegador producción anfitrión/copia/invitado/móvil correcto, cero acciones al consultar. No se han ejecutado ataques ni turnos en este ensayo.

Siguiente núcleo local, actor_references.py: selección de actor conocido y referencia de identidades/PNJ/paquete/revisiones, sin estadísticas en el DTO público. Rechaza otro propietario, ficha de jugador como objetivo, actor oculto/desconocido y referencias caducadas antes de cualquier dado. Trece pruebas junto a actores/perfiles correctas. Aún no conectado al runtime ni a solicitudes de campaña. Esta selección no acredita presencia en escena, alcance, visibilidad actual, turno ni legalidad de una acción; esos requisitos deben resolverse en la siguiente capa antes de aplicar efectos.

Integración local del primer bloque: `create_pack_actor` prepara una ficha completa únicamente desde un perfil explícito, PNJ de ficción existente y decisiones de todas sus etapas, con permiso provided-profile. API técnica del anfitrión, entre intervenciones resueltas; todavía no hay preparación automática de actores al importar aventura. No se requiere un anfitrión calculando estadísticas: los cálculos son del runtime, pero la selección del perfil/opciones sigue siendo preparación técnica pendiente de automatizar.

El registro privado conserva controlador director, perfil, ficha y pruebas de creación. Los actores no se convierten en personajes del jugador al copiar y no pueden usar sus rutas de intervención. El creador normal de jugadores no se usa por defecto. La misma semilla duradera de acción cubre todas las tiradas nuevas de preparación; falta de guardado y recuperación con cliente Firestore nuevo conservan ficha/dados. El reintento confirmado no vuelve a crearlos. Copia reproduce desde los dados registrados sin RNG y rechaza cambios de campos, propietario o evidencias. Validación final: 451 pruebas completas con emulador correctas sin omisiones (178,560 s); once pruebas de núcleo/perfiles posteriores cubren también actor vacío sin paquete e intento de hablar por PNJ, correctas.

La proyección no incluye fichas ni trazas de actores, tampoco para el anfitrión que juega. Solo publica nombre/id y campos explícitamente compartidos de PNJ ya conocidos; los demás actores quedan fuera. El diario muestra esos campos ya cargados sin acciones remotas. API HTTP y Waitress de recuperación correctas; navegador local anfitrión/invitado/móvil correcto, preparación real sobre doble local y apertura simulada identificada. Suite completa final pendiente. No se han implementado ataques contra objetivos, efectos entre fichas ni turnos automáticos: siguientes bloques 2–5 de este contrato. Las fórmulas del ejemplo son propias CC0, no nuevos PNJ certificados de Pathfinder.

## Límite actual que debe eliminarse

Los PNJ del diario son registros de ficción, no fichas de adversarios. Las acciones del paquete actual calculan campos del personaje que actúa. Un nombre en el relato o un vínculo de PNJ no autoriza a inventar estadísticas, descontar puntos de otra ficha o resolver un conflicto por prosa.

## Contrato de estado

Un actor reglamentario debe tener identidad opaca estable, ficha validada por el mismo paquete, fuente/preparación trazable, controlador y visibilidad explícitos. Un registro de PNJ puede enlazarlo, sin convertir personajes jugadores en PNJ ni dar a la IA control sobre ellos. Crear un adversario no consiste en copiar estadísticas inventadas a un registro de ficción.

El primer bloque utilizará un objetivo de acción explícito. Su identidad, paquete y revisión quedarán ligados a la solicitud antes de tirar. Revisiones incompatibles, un objetivo no permitido o una acción ya ilegal se rechazarán antes de obtener dados. Los efectos sobre actor y objetivo, la traza y cualquier consecuencia deben confirmarse atómicamente; reintentar conserva dados y resultados. La copia reproduce las dos fichas, orden y pruebas sin inferir ni tirar.

Lecturas de campos del objetivo y efectos sobre ellos requieren capacidades optativas de paquete. Las fórmulas existentes conservan ámbito y semántica; no reinterpretar referencias antiguas ni migrar silenciosamente solicitudes capturadas. No introducir fórmulas universales de impacto, daño, resistencia, iniciativa o muerte: cada paquete define únicamente las operaciones que el motor soporte y la fuente justifique.

## Permisos y presentación

- Un jugador conserva decisiones y control de su personaje. Ambigüedad de objetivo/opciones se aclara antes de resolver.
- La automatización puede controlar actores no jugadores autorizados; no usar el permiso del anfitrión para ejecutar decisiones ajenas.
- Conocer el nombre de un PNJ no implica conocer toda su ficha. El estado privado del adversario no puede filtrarse por la traza, el contexto de un jugador, el registro de cambios o una consulta de ids.
- Las pruebas completas de reproducción siguen en el estado privado; la vista pública muestra solo los resultados y sus orígenes permitidos.
- Selección de objetivo y previsualización con datos ya cargados son locales. Ninguna llamada a IA por calcular modificadores, impacto, daño o activar un botón de selección.
- Una secuencia automática confirmable debe agrupar cambios y evitar una escritura remota por cada modificador, condición o dado. No ocultar límites ni trasladar administración mecánica al jugador para ahorrar.

## Orden de integración y aceptación

1. Registro de actores y privacidad, con fichas deterministas, referencias de ficción y copia; sin prometer todavía resolución contra objetivos.
2. Ámbito de objetivo y efectos en el runtime; ejemplos propios, requisitos y casos límite antes de conectar narración.
3. Solicitud vinculada a las revisiones y confirmación conjunta de ambas fichas; fallos antes/después del commit, reintentos, concurrencia y recuperación con cliente nuevo.
4. Declaración/selección de objetivo, resultados canónicos y continuación conectada con los hechos reales.
5. Secuencias de PNJ según capacidades y reglas verificadas del paquete; después conexión con fichas del tablero.

Probar adversario oculto, objetivo cambiado, actor ajeno, revisión caducada, incapacidad sobrevenida, efecto condicional no aplicado, dos acciones concurrentes y copia manipulada. No anunciar el hito de primera aventura autónoma por tener una ficha de PNJ o un botón de ataque: requiere el recorrido completo definido en PRODUCTO.md.
