# Dirección de producto: mesa al estilo de Roll20

La aplicación debe aproximarse lo máximo posible a Roll20 en experiencia y capacidades de mesa virtual, añadiendo maestro de juego de IA y gestión automática de la partida. Se toma como referencia la [mesa de Roll20](https://help.roll20.net/hc/en-us/articles/360039734913-Tabletop-Overview): superficie de juego, fichas, herramientas y acceso a información durante la sesión.

Las tres bases son inseparables: mesa virtual familiar, automatización que permita a los jugadores centrarse en rolear y mínimo coste de IA/Firebase. No se afirma equivalencia funcional completa con Roll20.

Se aplica ingeniería inversa funcional: contratos documentados, implementación propia y pruebas de los gestos. La evidencia, matriz y diferencias están en [COMPATIBILIDAD_ROLL20.md](COMPATIBILIDAD_ROLL20.md). La primera ampliación incluye mano/botón derecho, zoom, arrastre con ruta y puntos intermedios, regla arrastrable, doble clic y atajos. Los recorridos se previsualizan localmente y conservan la confirmación reglamentaria antes de guardar.

## Primer recorrido disponible

Revisión visual9nov: la superficie de juego se diferencia como tablero de papel, manteniendo cuadrícula, geometría y estados reales. Conversación más ancha, escena antes de acciones y preparación de ficha plegada; encabezado compacto en móvil y herramientas manuales bajo excepciones. Tipografía sin descargas externas. Es presentación propia para el recorrido individual acotado, no una observación nueva ni equivalencia visual certificada con Roll20; no se han añadido mapas ilustrados, obstáculos ficticios, capas o visibilidad. Arrastre, regla, zoom y permisos conservan los contratos probados. Capturas locales antes/después y estado comprensible en la página de avance indicada en PRODUCTO.md.

Adaptación propia de claridad: diario de lectura con correcciones plegadas y tiradas libres de ficha bajo demanda, con selector agrupado y un único botón. Avisos de salud y solicitudes de la conversación siguen visibles. Elegir o consultar no persiste ni llama IA. No se atribuye este diseño a observación directa de Roll20; responde a la directiva de sencillez. Navegadores de diario, creador, pruebas de ficha, dos jugadores y recuperación/muerte verifican los recorridos afectados.

La directiva de sencillez de AGENTS.md se aplica también a la mesa: ayuda breve según selección/turno/acciones, ataque explicado cuando falta cercanía o acción, y controles de recorrido solo al prepararlo. Corrección excepcional, finalización manual y opción de automatización se consultan bajo «Reglas cubiertas y excepciones». Las decisiones básicas y los avisos de automatización pausada siguen visibles. No cambia reglas ni permisos; la presentación y las ayudas son locales. Evidencia de esta adaptación propia en USABILIDAD.md; no se atribuye al comportamiento observado de Roll20.

En escritorio desde 1100 píxeles, el tablero permanece visible junto al panel derecho de conversación, diario, documentos o dados. El grupo se muestra a la izquierda. En pantallas pequeñas, los paneles se alternan mediante pestañas para conservar espacio y acceso táctil. No se duplica el historial ni se abren suscripciones remotas para la vista dividida.

| Área | Estado actual |
|---|---|
| Mesa | Cuadrícula 20×20, zoom y desplazamiento por barras; muros y terreno difícil declarados |
| Fichas | Selección pulsando una ficha controlada, PG en el tablero, señal de turno y acceso a la hoja desde el grupo |
| Movimiento | Recorrido con coste, validación y confirmación; paso de5pies voluntario y validado en patio1.16, sin otros desplazamientos ese asalto; reglas especiales todavía limitadas |
| Medición | Dos pulsaciones marcan origen y destino; distancia geométrica 5/10 pies, local, sin mover fichas ni guardar cambios |
| Chat y dados | Conversación, narración del director, historial de reglas y dados rápidos sin activar IA |
| Combate | Iniciativa, acción estándar/movimiento, ataque cuerpo a cuerpo básico y estados descritos en [COMBATE.md](COMBATE.md) |
| Adversarios | Turnos locales automáticos opcionales: selección de objetivo, movimiento seguro, ataque y devolución del control al jugador |
| Información | Creador automático de humano guerrero 1, hojas calculadas o edición manual avanzada, diario y manuales privados por páginas |
| Maestro | Claude Haiku conectado a la ficción y al estado público; puede solicitar pruebas básicas que valida el motor, descritas en [PRUEBAS_PERSONAJE.md](PRUEBAS_PERSONAJE.md). Ataques, efectos y demás declaraciones mecánicas siguen su cobertura específica |

Consulta progresiva9nov: ficha preparada de PNJ muestra valores actuales yfuentes antes de ofrecer corrección manual explícita; los avisos distinguen PNJ/personaje propio. NPCsinseguimiento de otra escena quedan accesibles bajo consulta local; jugadores ypacientes no se relegan. La agrupación solo presenta datos ya recibidos; visibilidad servidor/niebla siguen pendientes. Ruta/acuerdo/combate/regreso/copia/teclado/tacto yrecuperación verificadas en nuestra app, sin nueva observación de Roll20.

Navegación propia de teclado9nov: Tab entra una vez enel tablero, flechas recorren casillas sin mover fichas, Intro usa herramienta seleccionada ymovimiento conserva confirmación. Tab sale alcontrol pertinente; Esc cancela. Foco visual yselección distintos, etiquetas de terreno/ficha/PG/turno yrepintado sin perder foco. Contraste de foco ygestos ratón/táctil verificados enChromium; fuente APG yalcance enUSABILIDAD. Sin nuevas llamadas deIA oestado remoto por navegación.

Orientación propia10nov: el tablero muestra primero asalto y turno actual. El orden completo de iniciativa, total y dados se despliega localmente con teclado o toque; conserva consulta/foco mientras avanzan asaltos y desaparece al terminar el combate. Respeta orden validado por motor, sin nueva tirada ni cálculo de reglas. initiative-disclosure-local-final.log y initiative-tabletop-regression.log; captura móvil en informe. No observación nueva ni equivalencia directa con tracker de Roll20.

Prioridad visual propia10nov: mapa antes del formulario de ataque, con confirmación de recorrido inmediata tras la superficie. Mismo DOM/controles/reglas, sin nuevas posiciones ni obstáculos. Primera vista móvil390×844 pasó de57,55px de mapa a varias filas visibles; Tab conduce del tablero a objetivo/ataque, y la guía indica dónde encontrarlos. board-map-first-guidance-final.log1.16, gestos y legado1.9 correctos; no observación nueva de Roll20. Desplazamiento táctil nativo CDP desde la guía alcanza el botón sin scroll programático: board-map-first-native-touch.log1.16 correcto, sin POST/estado por acceder; no prueba de todos los dispositivos físicos.

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
