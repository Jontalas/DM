# Dirección de producto: mesa al estilo de Roll20

La aplicación debe aproximarse lo máximo posible a Roll20 en experiencia y capacidades de mesa virtual, añadiendo maestro de juego de IA y gestión automática de la partida. Se toma como referencia la [mesa de Roll20](https://help.roll20.net/hc/en-us/articles/360039734913-Tabletop-Overview): superficie de juego, fichas, herramientas y acceso a información durante la sesión.

Las tres bases son inseparables: mesa virtual familiar, automatización que permita a los jugadores centrarse en rolear y mínimo coste de IA/Firebase. No se afirma equivalencia funcional completa con Roll20.

Se aplica ingeniería inversa funcional: contratos documentados, implementación propia y pruebas de los gestos. La evidencia, matriz y diferencias están en [COMPATIBILIDAD_ROLL20.md](COMPATIBILIDAD_ROLL20.md). La primera ampliación incluye mano/botón derecho, zoom, arrastre con ruta y puntos intermedios, regla arrastrable, doble clic y atajos. Los recorridos se previsualizan localmente y conservan la confirmación reglamentaria antes de guardar.

## Primer recorrido disponible

En escritorio desde 1100 píxeles, el tablero permanece visible junto al panel derecho de conversación, diario, documentos o dados. El grupo se muestra a la izquierda. En pantallas pequeñas, los paneles se alternan mediante pestañas para conservar espacio y acceso táctil. No se duplica el historial ni se abren suscripciones remotas para la vista dividida.

| Área | Estado actual |
|---|---|
| Mesa | Cuadrícula 20×20, zoom y desplazamiento por barras; muros y terreno difícil declarados |
| Fichas | Selección pulsando una ficha controlada, PG en el tablero, señal de turno y acceso a la hoja desde el grupo |
| Movimiento | Recorrido con coste, validación y confirmación; reglas especiales todavía limitadas |
| Medición | Dos pulsaciones marcan origen y destino; distancia geométrica 5/10 pies, local, sin mover fichas ni guardar cambios |
| Chat y dados | Conversación, narración del director, historial de reglas y dados rápidos sin activar IA |
| Combate | Iniciativa, acción estándar/movimiento, ataque cuerpo a cuerpo básico y estados descritos en [COMBATE.md](COMBATE.md) |
| Adversarios | Turnos locales automáticos opcionales: selección de objetivo, movimiento seguro, ataque y devolución del control al jugador |
| Información | Hojas editables, diario, referencias a manuales y documentos PDF privados |
| Maestro | Claude Haiku conectado a la ficción y al estado público; interpretación mecánica de declaraciones libres aún pendiente |

## Adversarios automáticos

La opción aparece activada al preparar un combate nuevo desde la interfaz; el anfitrión puede desactivarla o tomar el control durante el combate. Las partidas anteriores no cambian de modo automáticamente. Los clientes API anteriores que no envíen `automateEnemies` mantienen control manual.

El controlador no usa IA: busca una ruta de menor coste hacia un objetivo atacable, mueve como máximo una acción de movimiento y ataca si llega al alcance de su arma. Evita casillas ocupadas, muros, cortes de esquina y salir de posibles casillas amenazadas. No simula ataques de oportunidad ni atraviesa reglas no implementadas para completar un turno.

Un perfil incompatible o recorrido no verificable pausa la automatización con un motivo visible. El anfitrión puede resolver la excepción, reintentar las acciones restantes o desactivar el control automático. El sistema respeta las acciones ya gastadas. Nunca elige movimientos ni ataques de un personaje jugador.

Los turnos sin acciones de personajes caídos se saltan, aplicando la estabilización cubierta al entrar en su turno cuando procede. Si no queda ningún jugador consciente, el ciclo se detiene para revisar el desenlace. El controlador no declara una muerte colectiva, no ejecuta caídos ni decide rescates por los jugadores.

Todas las consecuencias de finalizar un turno y de los turnos automáticos inmediatamente siguientes se guardan en una sola confirmación de campaña. No hay una escritura adicional por casilla ni una llamada de IA por enemigo.

## Próximas capacidades para acercarse a la referencia

1. Mapas con imágenes y escenas, biblioteca de recursos y fichas visuales; reutilizar recursos y controlar transferencia/almacenamiento.
2. Capas y permisos de visibilidad, niebla de guerra y herramientas de anotación/medición más completas. La ocultación debe aplicarse también en el servidor, no solo en la pantalla.
3. Hojas con creación y cálculos reglamentarios, acciones desde la ficha y mayor cobertura de condiciones, conjuros y combate.
4. Maestro de IA que proponga acciones estructuradas y sucesos conectados con el motor, con contexto acotado y validación de todas las consecuencias.
5. Gestión de encuentros y escenas con menos preparación administrativa, ampliando los adversarios más allá del perfil básico.

Estos puntos son alcance pendiente, no controles que ya funcionen. La automatización mecánica se implementa mediante código y las herramientas de interfaz se ejecutan localmente; la IA se reserva para el trabajo narrativo e interpretativo necesario.
