# Actores reglamentarios y objetivos de acciones

Siguiente capacidad general pendiente. Este contrato no anuncia combate genérico ni reemplaza las reglas verificadas del módulo Pathfinder. La prueba inicial usará ficción y reglas propias; trasladar una mecánica de un manual exige consultar sus originales y registrar edición/páginas.

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
