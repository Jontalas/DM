# Ingeniería inversa funcional de Roll20

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

- [Mesa y navegación](https://help.roll20.net/hc/en-us/articles/360039734913-Tabletop-Overview).
- [Zoom](https://help.roll20.net/hc/es/articles/360043082213-Herramienta-de-Zoom).
- [Fichas, permisos y ajustes](https://help.roll20.net/hc/en-us/articles/360039674573-Token-Features).
- [Atajos avanzados](https://help.roll20.net/hc/pt/articles/360039178974-Atalhos-Avan%C3%A7ados).
- [Herramientas heredadas y regla](https://help.roll20.net/hc/fr/articles/14953988339735-Barre-d-outils-h%C3%A9rit%C3%A9e). La documentación heredada no prueba el comportamiento de todas las variantes actuales.
- [Recorridos y puntos intermedios en el modelo público de objetos](https://help.roll20.net/hc/en-us/articles/360037772793-Mod-Scripts-Objects).
- [Tiradas desde la hoja y resultado en el chat](https://wiki.roll20.net/Roll_Dice).

## Matriz de interacción

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
| RUL-01 | Medición mediante arrastre | Regla local entre centros de casilla, con línea y distancia Pathfinder 5/10 pies; también conserva medición por dos pulsaciones. Sin difusión a otros jugadores ni variantes sin ajuste/corner | Navegador: línea, distancia, zoom y cero cambios de versión |
| KEY-01 | Atajos avanzados de selección y mano | Subconjunto S y A activo por defecto; no se activa al escribir o con un diálogo abierto. La preferencia opcional de referencia sigue pendiente | Navegador: cambio de herramienta y escritura intacta |
| KEY-02 | Acceso por teclado a chat, diario y dados | C, J y D; doble C enfoca el chat. D abre nuestro panel de dados, no una ventana idéntica. Q es un acceso propio a medición; no implementa todas las secuencias Q de referencia | Navegador: paneles, foco e integridad del texto |
| TOUCH-01 | Experiencia adaptable de mesa | Arrastre táctil de fichas controladas y mano para desplazar. Compatibilidad probada en Chromium emulando táctil; no en todos los dispositivos | Navegador: vista móvil y previsualización sin guardado |

## Adaptaciones primordiales

- El arrastre no altera inmediatamente posiciones ni consume movimiento. Tras confirmar, el servidor valida el recorrido y guarda una acción identificada. Los casos de ataques de oportunidad aún no automatizados requieren la revisión existente; no se ignoran por imitar un gesto.
- El controlador de adversarios y las reglas automáticas siguen siendo deterministas y comparten la confirmación de campaña. La IA aporta ficción e interpretación donde corresponde, sin intervenir en zoom, selección o cada casilla.
- No se copian atributos de integración, API de extensiones o formatos de objetos que no necesitamos. El objetivo de compatibilidad es la experiencia del jugador y la conducta de las herramientas.
- Ningún gesto de cámara, previsualización, medición, atajo o inspección de una ficha genera operaciones de base de datos ni inferencias. Las consultas periódicas preexistentes siguen generando lecturas; un movimiento confirmado continúa teniendo el coste de persistencia habitual.

## Cobertura pendiente prioritaria

Mapas con imágenes y biblioteca de recursos; páginas/escenas; capas; visibilidad, niebla e iluminación con filtrado en el servidor; selección múltiple, redimensionado y rotación; propiedades y marcadores de fichas; menús contextuales completos; herramientas de dibujo; medición compartida y variantes; arrastre con validación automática completa al soltar; hojas reglamentarias; más mecánicas y dirección estructurada por IA.

Estos elementos no están certificados como implementados. La matriz se ampliará con sus fuentes, pruebas y excepciones conforme avance el desarrollo.

## Reproducción de las pruebas

```powershell
node test_tabletop_controls.cjs
node test_tabletop_browser.cjs
node test_browser.cjs
node test_sync.cjs
.\.venv\Scripts\python.exe -m unittest discover
```

Las pruebas de navegador requieren la herramienta local Playwright descrita en [COMBATE.md](COMBATE.md). Ejecutan un servidor desechable con datos sintéticos. Las pruebas geométricas recorren los 160.000 pares de casillas del tablero, además de límites y puntos intermedios. Las de interfaz verifican que los gestos locales no envían `/api/action` y que confirmar un movimiento produce exactamente un envío. No son pruebas ejecutadas contra Roll20.
