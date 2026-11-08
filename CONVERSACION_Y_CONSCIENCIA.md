# Hablar y declarar acciones requiere consciencia

El motor ya validaba contenido y propietario del hablante antes de llamar al director. Faltaba el estado clínico: una ficha inconsciente o muerta podía enviar palabras/acciones como personaje. Esto también permitía una llamada de IA que no debía producirse.

Se contrastó nuevamente el original Devir, Reglas básicas PDF190–191/folios189–190, para daño, inconsciencia/muerte; la recuperación de consciencia de PDF191–192 sigue en `pf_recovery`. Incapacidad consciente a0 o con PG negativos no equivale a inconsciencia: conserva el habla breve gratuita, con los límites ya documentados de movimiento/acción fatigosa en PDF184/189/568. No se introduce pérdida de PG o coste de acción por formular una pregunta.

En Pathfinder, `engine.talk` rechaza `action`/`dialogue` si la ficha seleccionada no está consciente. Sin ficha seleccionada, también bloquea si el usuario tiene PJ pero ninguno está consciente: el nombre del jugador no permite eludir el límite. La comprobación de propietario sigue anterior. Un anfitrión tampoco hace hablar a un PNJ inconsciente; puede dejar una nota explícita. `ooc` y `private` permanecen disponibles, así como conversar sin PJ creado todavía. No se impone el cálculo Pathfinder a otros sistemas.

El servidor valida antes de búsqueda, reserva de inferencia, proveedor y commit; el rechazo conserva el estado. La interfaz aplica la comprobación local al enviar y cambiar hablante/tipo, explica el motivo junto al campo con `aria-describedby` y desactiva enviar. Ctrl+Enter tampoco genera POST. Se puede seguir escribiendo un borrador y elegir comentario fuera de personaje/nota privada. Finalizar una acción o recuperar un envío recalcula el botón, evitando habilitarlo por error desde un `finally`.

Este bloque comprueba el estado determinista de PG y consciencia existente. No interpreta condiciones libres como «dormido» o «paralizado» ni certifica todos los impedimentos de habla. Una declaración de acción consciente sigue necesitando la validación reglamentaria específica; poder escribir no ejecuta ni autoriza esa acción. Las respuestas ya guardadas no se reescriben.

Pruebas específicas: dueño/inconsciencia/muerte con hablante explícito o por defecto, acción/diálogo, rechazo atómico,0PG y negativo consciente sin coste, notas del jugador y PNJ administrativo. HTTP/emulador rechaza con y sin director antes de buscar/reservar/llamar/guardar. Navegador local con preparación clínica explícita verifica ayuda móvil/táctil, teclado sin POST, nota permitida y diálogo a0PG, además de restablecer correctamente el botón tras resolver. Permisos entre dos participantes, recuperación de envíos, Cairn y cambio de sistema conservados. Cero inferencias reales nuevas para esta corrección.

Regresión final:823 completas correctas (211,078s), .deps/conversation-health-final-tests.log. Sin cambios del motor tras arrancar la suite.
