# Ingeniería inversa funcional de Roll20

Tablero: marcas locales !/…/↓/× para incapacitado/inconsciente estable/moribundo/muerte, derivadas de clasificación existente sin nuevos efectos ni interpretar conditions. Leyenda progresiva en ayuda, salud accesible en casilla, identidad/PG/selección conservados. current-reviewed1.16 y legacy-help-final1.11 verifican caída orgánica y probes locales restaurados, sanos sin marca, ayuda/zoom22-44-80 sin solapamiento,0API/estado por consulta; gestos correctos. Captura clínica1.16 real del fixture tras restaurar, dados simulados; informe verificado. Adaptación propia sin observación nueva de Roll20, no nuevas reglas. Accesos edb9de4/Render7692875376 verificados públicamente.

Movimiento: la preparación anticipa muros, esquinas bloqueadas, ocupación y límites de la acción de movimiento ya validados por el servidor. Explica cómo corregir el camino y distingue las excepciones pendientes de cobertura de las reglas universales. Consulta local, sin IA ni escrituras. Fuente original revisada visualmente: Reglas básicas PDF194/folio193; motor sin cambios. Evidencia movement-preflight-{baseline,geometry,budget,courtyard-regression}.log, teclado/móvil/estado idéntico durante previsión, ruta1.16 completa con paso/reserva; controles160000rutas correctas. No nueva observación directa de Roll20 ni equivalencia completa.

Objetivo obligatorio: máxima fidelidad viable a la mesa de Roll20 en comportamiento, organización e interacciones, incorporando director de IA, resolución automática de la partida y mínimo coste. La comparación se realiza por funciones verificables y diferencias explícitas.

## Método y evidencia

1. Investigar documentación pública y comportamientos observables de cada herramienta.
2. Describir entrada, permisos, respuesta visual, cambios de estado y casos límite.
3. Implementar el comportamiento en nuestro código y añadir pruebas de interacción.
4. Registrar equivalencias parciales y adaptaciones. Cuando se disponga de observación directa, comparar ambas mesas con el mismo recorrido y actualizar la evidencia.

Revisión del 19 de octubre de 2026: se consultó documentación oficial de Roll20. Las pruebas automatizadas y capturas corresponden a nuestra aplicación local. **No se abrió ni instrumentó una partida interactiva de Roll20, no se inspeccionó su implementación interna y no se certifica equivalencia entre ambas aplicaciones.** Esta fase constituye reconstrucción funcional a partir de contratos documentados.

Para la ampliación de botones de tirada de la hoja se consultó el extracto indexado de la Wiki de Roll20; el acceso directo a esa página devolvió 403. La equivalencia sigue limitada al contrato de pulsar un botón y publicar una tirada, sin afirmar una comparación interactiva directa.

Posteriormente se consultó la [documentación oficial completa de Pathfinder by Roll20](https://help.roll20.net/hc/en-us/articles/360037773733-Pathfinder-by-Roll20), incluidos cálculo automático, botones de tirada y lanzamiento del Charactermancer de nivel 1. La ampliación del creador sigue una implementación propia de pasos y revisión de elecciones; no reproduce todavía todas sus opciones.

## Fuentes de referencia

- [Page Menu & Folders](https://help.roll20.net/hc/en-us/articles/360039675413-Page-Menu-Folders), consulta documental7 de noviembre de2026. Separación de página del grupo y copia de fichas; acceso/gestión del GM. Ruta1.4/1.5 desplegada con escenas propias; ampliación local1.6 de regreso y objetivo persistente en ESCENAS_TABLERO.md. Sin observación directa de partida.

- [Mesa y navegación](https://help.roll20.net/hc/en-us/articles/360039734913-Tabletop-Overview).
- [Zoom](https://help.roll20.net/hc/es/articles/360043082213-Herramienta-de-Zoom).
- [Fichas, permisos y ajustes](https://help.roll20.net/hc/en-us/articles/360039674573-Token-Features).
- [Atajos avanzados](https://help.roll20.net/hc/pt/articles/360039178974-Atalhos-Avan%C3%A7ados).
- [Herramientas heredadas y regla](https://help.roll20.net/hc/fr/articles/14953988339735-Barre-d-outils-h%C3%A9rit%C3%A9e). La documentación heredada no prueba el comportamiento de todas las variantes actuales.
- [Recorridos y puntos intermedios en el modelo público de objetos](https://help.roll20.net/hc/en-us/articles/360037772793-Mod-Scripts-Objects).
- [Tiradas desde la hoja y resultado en el chat](https://wiki.roll20.net/Roll_Dice).

## Matriz de interacción

Ampliación propia del 4 de noviembre de 2026: las rutas individuales de investigación enlazan lugares mediante salidas validadas, con elección del jugador y persistencia de pistas. No equivalen al gestor de páginas, separación del grupo, visibilidad, capas ni traslado de fichas de Roll20. No se ha observado directamente ese recorrido en Roll20; la evidencia de nuestra aplicación está en `test_routes_browser.cjs`, HTTP y pruebas del motor. Véase INVESTIGACIONES.md para límites de escenas y coste.

Las filas probadas indican cobertura de **nuestra** implementación frente al comportamiento descrito; queda pendiente la comparación directa en Roll20.

| ID | Referencia documentada | Implementación actual y diferencia | Prueba |
|---|---|---|---|
| NAV-01 | Desplazamiento por barras y arrastre con botón derecho | Ambos; además herramienta de mano con botón izquierdo o táctil. Solo cambia la cámara local | Navegador: desplazamiento en ambos ejes y cero escrituras |
| NAV-02 | Control deslizante, rueda modificada y teclas de zoom | Alt/Ctrl/Meta + rueda, +/−, deslizador y reinicio por doble clic. Mantiene el punto bajo el cursor; rango actual 50–250 %, no todos los ajustes de referencia | Navegador: zoom, anclaje, reinicio y regla redibujada |
| TOK-01 | Control por jugador asignado y control del maestro | Propietario único y anfitrión; sin asignación múltiple por ficha | Navegador: invitado mueve su personaje y no el adversario; servidor verifica permisos |
| TOK-02 | Doble clic abre ajustes de la ficha | Doble clic abre nuestra hoja del personaje controlado. Es una adaptación; no reproduce todavía el diálogo de propiedades de token | Navegador: apertura y nombre correcto |
| SHEET-01 | Botones de tirada de la hoja publican el resultado en el chat | Características, salvaciones y habilidades preparadas con modificadores guardados. Solicitudes del director con CD y resolución por propietario. Sin macros ni hojas de clase completas | Python/HTTP: permisos, cálculo y deduplicación; navegador: dos sesiones y móvil |
| CREATE-01 | Charactermancer de nivel 1 y atributos derivados de la hoja | Creador en cuatro pasos, elecciones, vista previa local y validación del servidor. Humano guerrero 1 con opciones acotadas; hoja y perfil de combate calculados. Sin todas las razas/clases ni subida de nivel | Python: 72 combinaciones de paridad con JavaScript; HTTP/Waitress: persistencia y permisos; navegador: creación hasta ataque, sin estadísticas manuales |
| MOV-01 | Movimiento de fichas con recorrido y puntos intermedios | Arrastre prepara ruta ajustada a casillas; Espacio fija puntos y Esc cancela. **Soltar no guarda**: se conserva la confirmación existente para revisar excepciones de reglas | Navegador: ruta, puntos, cancelación, un solo guardado confirmado |
| SCENE-01 | Páginas del grupo y fichas situadas en cada página | Escenas por salida narrativa elegida, PJ cambia de lugar y PNJ permanece; terreno/posiciones y hallazgos recordados.1.6 local conserva objetivo global tras regresar. Sin cinta de GM, grupos separados, capas ni visibilidad; transición no calcula duración ni peligros | Motor/HTTP/Waitress: ámbitos, requisitos, pacientes remotos, copia/duplicados. Navegador: ruta original, regreso tras objetivo, hallazgos opcionales, diario, teclado y móvil;679 pruebas completas de la aplicación. Sin prueba directa de Roll20 |
| RUL-01 | Medición mediante arrastre | Regla local entre centros de casilla, con línea/extremos/valor visible y distancia Pathfinder5/10 existente; texto advierte que no incluye terreno/obstáculos ni es coste de movimiento. Conserva dos pulsaciones y acceso con teclado. Sin difusión a otros jugadores ni variantes sin ajuste/corner | Navegador: línea/valor/origen/20-5-0pies/borde/zoom/limpieza, un solo overlay y cero cambios de versión |
| KEY-01 | Atajos avanzados de selección y mano | Subconjunto S y A activo por defecto; no se activa al escribir o con un diálogo abierto. La preferencia opcional de referencia sigue pendiente | Navegador: cambio de herramienta y escritura intacta |
| KEY-02 | Acceso por teclado a chat, diario y dados | C, J y D; doble C enfoca el chat. D abre nuestro panel de dados, no una ventana idéntica. Q es un acceso propio a medición; no implementa todas las secuencias Q de referencia | Navegador: paneles, foco e integridad del texto |
| TOUCH-01 | Experiencia adaptable de mesa | Arrastre táctil de fichas controladas y mano para desplazar. Compatibilidad probada en Chromium emulando táctil; no en todos los dispositivos | Navegador: vista móvil y previsualización sin guardado |

Revisión propia9nov: creador mantiene cuatro pasos de personalización yofrece camino nombre/estilo→revisión→confirmar. Fichas preparadas se consultan antes de editar; PNJde otra escena sin seguimiento se agrupan localmente ypacientes/jugadores siguen visibles. Son adaptaciones de claridad verificadas con nuestros navegadores, sin observación directa nueva ni filtrado servidor/niebla añadidos.

Teclado de casillas9nov: extensión propia conentradaTab única, flechas defoco, Intro segúnherramienta yconfirmación de movimiento intacta; conserva atajosdocumentados ygestos existentes. Fuente APG yprueba enUSABILIDAD/test_tabletop_browser.cjs. No se atribuye este comportamiento aobservación nueva deRoll20. Borrar recorrido con teclado restaura foco útil y un tabstop sin mover ni cambiar actor; clear-path-focus-guidance-final y reserved-preview-final1.16 correctos, sin nueva observación de referencia.

## Adaptaciones primordiales

- Orientación propia10nov tras una transición confirmada: título de escena enfocado, guía local de investigación y salida visible. Se respeta navegación posterior; recuperar no realiza otro viaje ni tirada. Pruebas de teclado/móvil390×844 y respuestas perdidas. Adaptación para director automático y sencillez, sin nueva observación directa de Roll20.
- Adaptación propia del rol de jugador individual: en combate preparado, propietario con su PJ seleccionado apunta a la guardiana al pulsarla/Intro, en lugar de asumir control de PNJ por ser anfitrión. Selector de control manual y gestos de mesas generales se conservan. Cero persistencia/IA al apuntar; teclado/táctil comprobados. No se atribuye este cambio a observación directa de Roll20: responde a la dirección automática y agencia exigidas para esta app.
- Adaptación propia de Pathfinder para patio1.16: paso de5pies escogido con botón tras marcar una casilla, validado por servidor y sin revisión genérica de AdO. Conserva acciones, impide otro desplazamiento ese asalto y persiste la marca en copias. Fuentes originales y límites en COMBATE.md; pruebas unitarias/HTTP y recorrido local móvil/teclado. No se atribuye este control a observación directa de Roll20.
- El arrastre no altera inmediatamente posiciones ni consume movimiento. Tras confirmar, el servidor valida el recorrido y guarda una acción identificada. Los casos de ataques de oportunidad aún no automatizados requieren la revisión existente; no se ignoran por imitar un gesto.
- El controlador de adversarios y las reglas automáticas siguen siendo deterministas y comparten la confirmación de campaña. La IA aporta ficción e interpretación donde corresponde, sin intervenir en zoom, selección o cada casilla.
- No se copian atributos de integración, API de extensiones o formatos de objetos que no necesitamos. El objetivo de compatibilidad es la experiencia del jugador y la conducta de las herramientas.
- Ningún gesto de cámara, previsualización, medición, atajo o inspección de una ficha genera operaciones de base de datos ni inferencias. Las consultas periódicas preexistentes siguen generando lecturas; un movimiento confirmado continúa teniendo el coste de persistencia habitual.

## Cobertura pendiente prioritaria

Mapas con imágenes y biblioteca de recursos; páginas/escenas; capas; visibilidad, niebla e iluminación con filtrado en el servidor; selección múltiple, redimensionado y rotación; propiedades y marcadores de fichas; menús contextuales completos; herramientas de dibujo; medición compartida y variantes; arrastre con validación automática completa al soltar; hojas reglamentarias; más mecánicas y dirección estructurada por IA.

Estos elementos no están certificados como implementados. La matriz se ampliará con sus fuentes, pruebas y excepciones conforme avance el desarrollo.

Adaptación propia de orientación10nov: asalto y turno actual primero (texto Asalto en interfaz); orden íntegro ya validado por motor bajo consulta nativa, con total/dados y participante actual. Teclado/táctil, foco y apertura conservados durante asaltos, sin operaciones remotas por consultar. initiative-disclosure-local-final.log1.16 e initiative-tabletop-regression.log verifican nuestra app; no se ha realizado observación nueva del tracker de Roll20 ni se afirma reproducirlo por completo. Sin nuevas reglas ni tiradas. Véase MESA_VIRTUAL.md.

Presentación propia10nov: tablero antes de ataque y confirmación de movimiento junto al recorrido, sin cambiar MOV-01/TOK-01/KEY-01/TOUCH-01 ni duplicar controles. board-map-first-guidance-final.log1.16 verifica primera vista móvil≥3filas y Tab a objetivo/ataque; board-map-first-tabletop-regression.log gestos intactos y legado1.9 correcto. No nueva observación ni afirmación de igualdad visual con Roll20. Desplazamiento táctil nativo CDP desde la guía alcanza el botón sin scroll programático: board-map-first-native-touch.log1.16 correcto, sin POST/estado por acceder; no prueba de todos los dispositivos físicos.

Adaptación propia de navegación10nov: desde hoja calculada/PNJ preparado se localiza su ficha en tablero actual por foco y resaltado, sin seleccionar/mover ni cambiar escena. Otra escena no ofrece traslado y contexto antiguo se rechaza. show-character-local-owner-touch-final.log, changed-context-final.log y prepared-token-and-remote-scene-final.log1.16 verifican nuestra app,0operaciones de juego por consultar. No nueva observación ni afirmación de equivalencia con funciones de navegación entre hojas/páginas de Roll20.

## Reproducción de las pruebas

```powershell
node test_tabletop_controls.cjs
node test_tabletop_browser.cjs
node test_browser.cjs
node test_sync.cjs
.\.venv\Scripts\python.exe -m unittest discover
```

Las pruebas de navegador requieren la herramienta local Playwright descrita en [COMBATE.md](COMBATE.md). Ejecutan un servidor desechable con datos sintéticos. Las pruebas geométricas recorren los 160.000 pares de casillas del tablero, además de límites y puntos intermedios. Las de interfaz verifican que los gestos locales no envían `/api/action` y que confirmar un movimiento produce exactamente un envío. No son pruebas ejecutadas contra Roll20.
