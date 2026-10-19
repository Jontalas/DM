# Premisas primordiales de la aplicación

## Referencia principal: mesa virtual al estilo de Roll20

La aplicación debe parecerse a Roll20 en la mayor medida viable, tanto en organización de la mesa como en las interacciones y capacidades de una mesa virtual. Esta referencia se combina obligatoriamente con un maestro de juego controlado por IA, automatización de la partida y mínimo coste de uso.

- Priorizar mapa/tablero y fichas como superficie central; chat y registro de tiradas, personajes, diario, documentos, herramientas e iniciativa accesibles durante la partida. En escritorio, poder ver el tablero y la conversación simultáneamente; adaptar la navegación a pantallas pequeñas.
- Ampliar progresivamente selección y movimiento de fichas, medición, mapas y escenas, recursos visuales, permisos, capas y visibilidad, hojas de personaje y acciones desde la ficha. Usar Roll20 como referencia funcional y de experiencia sin presentar capacidades pendientes como disponibles.
- El maestro de IA debe dirigir la ficción conectado con el estado real. Las reglas, dados, turnos, sucesos y consecuencias verificables se gestionan automáticamente por el motor; los jugadores conservan sus decisiones y el control de sus personajes.
- Las herramientas manuales complementan la automatización para preparación, excepciones y correcciones. No convertir la referencia a una mesa virtual en una obligación de administrar manualmente cada regla.
- Las interacciones de interfaz, selección, zoom, medición y consulta de datos ya cargados se resuelven localmente. No generar llamadas a IA ni operaciones de base de datos solo por navegar o cambiar de herramienta.
- Aplicar ingeniería inversa funcional a Roll20: documentar comportamientos observables y fuentes, convertirlos en contratos de interacción, implementarlos con código propio y probarlos. Buscar la máxima fidelidad de gestos, disposición y recorridos, además de apariencia. Registrar expresamente las adaptaciones exigidas por Pathfinder, automatización, IA y ahorro.
- Mantener una matriz de compatibilidad con comportamiento de referencia, estado implementado, pruebas y diferencias. Distinguir documentación consultada, observación directa en una sesión y prueba de nuestra aplicación; no afirmar equivalencia completa ni verificación directa cuando no se hayan realizado.

## Autoridad de los manuales en todo el juego

Los tres documentos aportados por el usuario son la referencia reglamentaria permanente de toda la aplicación: Reglas básicas de Pathfinder 1e, Bestiario y TREY. Deben fundamentar todos los sistemas, desde creación y progresión de personajes hasta exploración, interacción social, combate, conjuros, equipo, criaturas, encuentros y dirección de la aventura. Roll20 es el modelo de experiencia e interacción; no sustituye esas fuentes de reglas.

- Antes de implementar o modificar una mecánica, contrastar en los originales los apartados, tablas, prerrequisitos y excepciones pertinentes. Mantener trazabilidad de libro, edición y página PDF, distinguiendo folio impreso cuando se haya comprobado. La extracción de texto facilita localizar reglas; tablas ambiguas y datos sensibles al formato requieren comprobar visualmente el original.
- Pathfinder resuelve sus mecánicas y el Bestiario aporta las criaturas y sus capacidades. TREY complementa la dirección y los hechos inciertos dentro de su ámbito; no sustituye una regla aplicable de Pathfinder. Resolver discrepancias de forma explícita y documentada, sin inventar equivalencias ni atribuir una decisión casera al manual.
- El creador actual es un primer bloque acotado del creador final. Limitar las opciones ofrecidas a las implementadas y verificadas no autoriza a simplificar o cambiar silenciosamente sus reglas. Distinguir opciones reglamentarias elegidas para la campaña, límites temporales del motor y reglas caseras expresamente acordadas.
- Implementar las reglas verificadas en código determinista y catálogos reutilizables, con pruebas de sus cálculos y casos límite. Esta aplicación permanente de los manuales no exige releerlos remotamente ni enviarlos completos a la IA en cada acción. Recuperar únicamente los fragmentos pertinentes cuando haga falta resolver una consulta o interpretación; así se mantiene la autoridad reglamentaria y el ahorro.
- Si una mecánica no está verificada o no está cubierta, indicar la limitación y registrar su resolución excepcional. No presentar una aproximación, narración o salida de IA como cumplimiento certificado de las reglas. Revisar también las funciones existentes frente a estas exigencias.

## Experiencia de videojuego y automatización

La entrada al juego es prioritaria: crear un personaje jugable debe ser un recorrido guiado y automático al estilo del Charactermancer de Roll20. El jugador elige concepto y opciones legales; el motor valida y calcula la ficha. No dar por utilizable una función dependiente de personajes si exige preparar manualmente sus estadísticas. Ampliar razas, clases y niveles por bloques verificados, indicando la cobertura real.

La aplicación debe funcionar básicamente como un videojuego de rol para los jugadores. Estos declaran sus acciones, interpretan a sus personajes, interactúan entre sí y con el maestro de juego y tiran dados cuando corresponde. La aplicación debe encargarse automáticamente del funcionamiento del juego en la medida de lo posible.

- Automatizar la aplicación de reglas, validación de acciones, modificadores, dificultades, turnos, iniciativa, movimiento, recursos, daño, condiciones, duraciones, desencadenantes, sucesos y consecuencias conforme a Pathfinder 1e y TREY. Implementar progresivamente los casos pendientes; no inventar reglas para simular cobertura.
- El recorrido objetivo es: declaración del jugador, interpretación de su intención, comprobación de requisitos, solicitud de la tirada necesaria, resolución de reglas, aplicación de consecuencias y actualización compartida del estado y la narración. Solicitar aclaración solo cuando la intención o una decisión del personaje sea ambigua.
- No obligar al jugador ni al anfitrión a calcular modificadores, consultar tablas, editar fichas, descontar recursos o confirmar cada consecuencia que el motor pueda resolver con seguridad. Las herramientas manuales deben servir para excepciones y correcciones, no ser el recorrido habitual.
- Mantener la agencia del jugador: automatizar las mecánicas no autoriza a decidir lo que piensa, dice o elige su personaje. Explicar brevemente las tiradas y consecuencias relevantes; permitir revisar su origen y corregir resoluciones excepcionales con permisos adecuados.
- Usar código determinista para reglas y estado. La IA interpreta intenciones, dirige la ficción y propone acciones estructuradas cuando sea necesario; el servidor valida su legalidad y aplica los cambios. Una narración por sí sola no cambia el estado ni sustituye una tirada requerida.
- Resolver automáticamente los sucesos y desencadenantes verificables, incluidos los de TREY, sin trasladar al jugador el seguimiento administrativo. Para reglas aún no implementadas o situaciones sin resolución verificable, mostrar la limitación y ofrecer una adjudicación excepcional explícita.
- Integrar esta automatización con el mínimo coste de uso: la automatización de mecánicas no debe depender de una llamada de IA por cálculo, evento o cambio de ficha. Agrupar las consecuencias de una acción para evitar operaciones remotas redundantes, conservando consistencia y trazabilidad.
- Evaluar cada función por cuánto trabajo administrativo elimina al jugador y qué parte del recorrido completa. Distinguir siempre el objetivo de producto de la cobertura realmente implementada; la versión actual todavía contiene procedimientos manuales.

## Mínimo coste de uso

El uso de IA, base de datos y almacenamiento remoto debe ser el mínimo imprescindible en todo momento para ahorrar la mayor cantidad posible de dinero pagado por el uso de la aplicación. Esta premisa se aplica a toda función nueva, corrección y decisión de arquitectura.

- Resolver mediante código determinista o cálculo local todo lo que no requiera IA. Reservar la intervención del jugador para decisiones de su personaje, tiradas y aclaraciones necesarias; no trasladarle administración mecánica para ahorrar IA. Llamar al modelo solo cuando aporte una respuesta necesaria para la partida; evitar llamadas automáticas por navegación, sincronización o acciones administrativas.
- Reducir las llamadas y los tokens: enviar únicamente el contexto pertinente, limitar la salida y reutilizar resultados cuando sean válidos y respeten los permisos. Evitar duplicados y reintentos facturables innecesarios.
- Minimizar lecturas, escrituras, consultas y transferencias de Firebase. Evitar consultas periódicas sin necesidad, escrituras sin cambios y volver a cargar o indexar recursos que no han cambiado. Priorizar caché, consultas acotadas, agrupación de cambios y sincronización adaptativa cuando sean compatibles con la consistencia requerida.
- Conservar solo los datos e índices necesarios. Definir una política de retención y limpieza para datos temporales u obsoletos; proteger partidas, originales y copias necesarias antes de eliminar cualquier dato.
- Elegir la alternativa viable de menor coste total de alojamiento, IA, operaciones y transferencia. Explicar cualquier gasto recurrente nuevo y su necesidad; no activar servicios de pago adicionales sin autorización.
- Evaluar el coste por acción y con varios jugadores antes de implementar funciones. Documentar las llamadas y operaciones evitadas y las limitaciones pendientes; no presentar esta política como una optimización ya implementada.
- El ahorro debe preservar la seguridad, privacidad, persistencia, reglas del juego y coherencia entre jugadores. No reutilizar datos privados entre usuarios ni omitir validaciones para reducir operaciones.
