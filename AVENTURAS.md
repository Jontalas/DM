# Inicio de aventura y memoria de campaña

## Recorrido disponible

Tras crear un personaje con el asistente, el anfitrión puede pulsar «Iniciar aventura con IA» en Conversación. Elige o conserva la premisa; se respetan el tono y los límites guardados en la campaña. El director propone una apertura, objetivos y preparación privada. No se crean estadísticas de criaturas ni encuentros supuestamente equilibrados.

La misma respuesta estructurada contiene narración y memoria. El servidor valida campos, tamaños y tipos antes de guardar todo junto. La memoria pública aparece en Diario como «El hilo de la aventura»; las actualizaciones de lugar, objetivo y objetivos se reflejan en la mesa. La preparación generada del director se guarda aparte de las notas manuales. El anfitrión conserva acceso administrativo a los secretos; los invitados no reciben ese campo.

Durante una aventura iniciada, cada respuesta a acciones o diálogos conserva un resumen público y una memoria privada actualizados. Las intervenciones fuera de personaje y las consultas de reglas no actualizan la memoria. Al solicitar una tirada o mientras haya pruebas pendientes, no se confirma memoria nueva. Tras resolverlas, «Continuar con el resultado de la tirada» solicita narración basada en los resultados reales del motor, sin volver a tirar ni decidir una nueva acción del personaje. También se puede continuar declarando la siguiente acción.

Recargar, reanudar y exportar/importar conservan memoria y preparación. Las campañas anteriores siguen funcionando sin activar esta función: no se inicia ni se consume IA automáticamente al abrirlas. Activar la función respeta el historial existente y no borra notas, personajes o tiradas anteriores.

## Fronteras y límites

La memoria admite únicamente resumen, lugar, objetivo, lista de objetivos y preparación privada. No puede cambiar fichas, PG, inventario, recursos, dados, escenas, tiempo reglamentario, turnos ni terreno. Tampoco puede trasladar un combate activo. La validación es estructural: no demuestra por sí sola la corrección semántica de lo narrado o resumido. El registro conserva las intervenciones originales para revisión.

Esta entrega permite preparar y continuar ficción, pero todavía no cubre una aventura completa de Pathfinder sin excepciones humanas. Importación estructurada de aventuras, encuentros automáticos verificados, progresión y otros sistemas siguen pendientes. La preparación generada no equivale a un módulo completo de aventura con mapa y catálogo de encuentros.

Los secretos se excluyen de las respuestas de estado a invitados y de consultas reglamentarias. Las instrucciones al modelo le exigen no publicarlos indebidamente; esa instrucción no garantiza ausencia de filtraciones narrativas. Las notas privadas personales y los secretos antiguos del anfitrión siguen excluidos de la IA.

## Coste y recuperación

Iniciar usa una llamada al proveedor y una confirmación de estado. La memoria viaja en la respuesta narrativa habitual; no añade otra llamada ni una escritura independiente. Continuar tras una tirada usa una llamada explícita adicional para narrar su resultado. Abrir el formulario, consultar el diario, navegar y tirar dados no generan inferencias.

Se limita el resumen a 6.000 caracteres, la preparación a 8.000 y la lista a doce objetivos; el modelo recibe instrucciones de escribir cantidades menores. No se envía una segunda copia de la memoria privada como estado público. Las consecuencias mecánicas siguen dependiendo de sus módulos deterministas y sus fuentes verificadas; esta entrega no introduce reglas nuevas.

La deduplicación y la versión se comprueban antes de llamar a IA. Reenviar una acción confirmada no repite inferencia ni efectos. También se rechaza una segunda iniciación o continuación sin resultados nuevos. Una respuesta inválida no confirma un estado parcial, aunque la inferencia ya realizada puede tener coste. No hay reintentos facturables automáticos.

## Verificación local

test_adventure.py comprueba límites, permisos de inicio, aislamiento del contexto, campos mecánicos prohibidos y continuidad. test_server.py comprueba confirmación conjunta, reenvíos, recuperación, importación, resultados de pruebas y errores sin cambios parciales; esos mismos casos se ejecutan bajo Waitress mediante test_render.py.

test_adventure_browser.cjs recorre inicio, diario, secretos de invitados, prueba, continuación, recarga y pantalla de 390×844. Usa un proveedor simulado exclusivamente en test_browser_fixture.py, activado por TEST_ADVENTURE_FIXTURE. Esa ruta no forma parte del inicio de producción. Las pruebas del creador y las pruebas de personaje siguen pasando. La evaluación de una sesión real debe registrarse por separado y no inferirse de estas pruebas.

En esta entrega pasaron las 144 pruebas Python con el emulador oficial de Firestore, sin omisiones, además de los recorridos Playwright de aventura, creador y pruebas de personaje, la sincronización y 160.000 rutas geométricas. Se inspeccionó la captura del diario a 390×844. El emulador utiliza un proyecto demo y prefijos de prueba; no las campañas reales.
