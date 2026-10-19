# Tiradas de personaje y solicitudes del director

La ficha permite tirar Fuerza, Destreza, Constitución, Inteligencia, Sabiduría, Carisma, Fortaleza, Reflejos, Voluntad y habilidades preparadas. Una pulsación envía la acción; el servidor obtiene el d20, aplica el modificador guardado y registra el desglose en la conversación compartida. Abrir la ficha no consulta Firebase ni Claude.

## Preparación y alcance

Los modificadores de característica se calculan como suelo((puntuación − 10) / 2). Las tres salvaciones son **totales declarados**, que ya incluyen sus bonificadores; no se les vuelve a sumar la característica. Las habilidades preparadas se introducen una vez, una por línea, por ejemplo `Percepción | 8`. Solo deben prepararse habilidades legales para ese personaje y situación, con rangos, clase, equipo y demás modificadores ya verificados. El texto libre de habilidades anterior se conserva y no se interpreta automáticamente como números.

Una tirada libre desde la ficha muestra el total. Una solicitud del maestro añade CD y motivo: el jugador pulsa «Tirar d20 y resolver» y el motor determina éxito o fallo. Igualar la CD es éxito. En salvaciones, 1 natural falla y 20 natural tiene éxito; esta regla no se aplica a pruebas de característica o habilidad. Las fichas con condiciones anotadas o PG negativos se derivan a resolución asistida porque sus excepciones no están cubiertas.

Fuentes comprobadas en el original local: Reglas básicas PDF pp.16–18, características; p.87, pruebas de habilidad; pp.181–182, salvaciones y resultados naturales. No se certifica el cálculo de la progresión de clase, requisitos de entrenamiento o todos los modificadores circunstanciales. Tampoco se implementan aquí enfrentadas, elegir 10/20, efectos secundarios, daño o gasto de acciones. El resultado no modifica por sí solo PG, recursos ni la economía de acciones.

## Maestro de IA y permisos

Claude puede incluir hasta tres solicitudes estructuradas en su respuesta habitual. El esquema utiliza la función existente de [salidas estructuradas de Anthropic](https://platform.claude.com/docs/en/build-with-claude/structured-outputs). No se añade una llamada de IA para solicitar ni resolver el dado. El contexto indica qué personajes puede controlar la persona que interviene; el servidor vuelve a comprobar ese límite, la ficha, la prueba, CD y motivo. Una solicitud válida queda pendiente; una no ejecutable se transforma en propuesta de revisión. Una solicitud equivalente ya pendiente no se duplica.

La CD propuesta por el director es una adjudicación para esa situación salvo referencia verificada; se identifica como tal. El modelo tiene instrucciones de no narrar el desenlace antes de la tirada ni sustituir una decisión del jugador. El esquema y el motor verifican estructura y legalidad básica, no certifican la interpretación narrativa del modelo. Las consultas de reglamento no crean solicitudes. Resolver un dado tampoco dispara automáticamente otra narración facturable: la siguiente intervención usa el resultado del historial.

El anfitrión también puede solicitar y cancelar pruebas desde Conversación. Solo el propietario o el anfitrión puede resolver una solicitud. La CD y el personaje proceden del estado guardado, nunca de valores enviados por quien tira. Los invitados usan dados del servidor; el anfitrión puede registrar un dado físico verificado mediante la API. Los reenvíos conservan la deduplicación existente y una solicitud resuelta no puede repetirse con otro identificador.

## Coste y pruebas

Cada solicitud, cancelación o tirada utiliza una acción normal de campaña; se agrupan registro, resultado y retirada de la solicitud en una misma confirmación. No consulta índices o PDFs para calcular la tirada ni añade colecciones o suscripciones. Las solicitudes incluidas en una respuesta de Claude se guardan junto a esa misma intervención. El esquema y sus instrucciones aumentan ligeramente los tokens de la llamada narrativa existente; no se presenta esa llamada como gratuita.

`test_checks.py`, `test_claude_checks.py` y los casos HTTP heredados por Waitress cubren cálculo, permisos, manipulación de CD, datos inválidos, casos naturales, compatibilidad y reenvíos. `test_checks_browser.cjs` prueba dos sesiones, ficha, petición del anfitrión, resolución del jugador, persistencia, edición de habilidades y móvil. Las respuestas de Claude en las pruebas son simuladas explícitamente: no se afirma una prueba de inferencia real de este nuevo recorrido ni se consumió su API durante la validación.
