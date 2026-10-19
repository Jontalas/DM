# Crónicas · mesa de rol en español

Aplicación local cliente/servidor para Pathfinder **primera edición** y TREY. Esta entrega es una base funcional ampliable; **no completa todas las etapas solicitadas**. No contiene una aventura de respuestas prefijadas ni un director simulado.

## Iniciar

Requiere Python 3.11 o posterior con SQLite FTS5 (comprobado en Python 3.14 de este equipo). El servidor no necesita paquetes adicionales.

```powershell
cd C:\Users\Jonta\OneDrive\Proyectos\DM
python server.py
```

Abre **http://127.0.0.1:8787**. También puedes ejecutar `start.ps1`. Los originales se leen del Escritorio, sin modificarlos. Usa `BOOKS_DIR` si los cambias de carpeta.

## Director de IA real

La IA que escribió esta aplicación no es el servicio de IA que dirige las partidas. No se detectó Ollama ni un modelo configurado en esta sesión. El recorrido conversacional con un modelo real **no ha podido verificarse**.

Instala [Ollama](https://ollama.com/), descarga un modelo conversacional apropiado para tu equipo y mantenlo en ejecución. Consulta `ollama list` para copiar el identificador exacto de un modelo instalado. Antes de arrancar el servidor:

```powershell
$env:OLLAMA_MODEL = 'identificador-de-tu-modelo-instalado'
$env:OLLAMA_URL = 'http://127.0.0.1:11434'
python server.py
```

Integración real mediante [POST /api/chat](https://docs.ollama.com/api/chat), mensajes con contexto recuperado y salida JSON. No necesita clave para un Ollama local. La configuración reside en el servidor. No se instala ni descarga un modelo de varios GB sin conocer los recursos del equipo.

Si falta el modelo o falla el proveedor, el envío devuelve un error visible y no añade un turno falso. Puedes desmarcar «Responder con IA» para preparar personajes, conversar entre personas, tirar dados y usar los manuales. Eso es un modo de mesa asistida, no una partida dirigida por IA.

La respuesta narrativa puede proponer resoluciones pendientes, pero no modifica fichas ni tira dados por texto. El anfitrión valida cambios mediante el motor. Las respuestas sobre reglas muestran los fragmentos y páginas recuperados; su corrección semántica sigue dependiendo del modelo y de la revisión humana. No se envían los libros enteros en cada turno.

## Funciones disponibles

- Campaña con tono, límites de contenido, objetivo y dificultad declarada; continuación mediante credencial guardada en el navegador.
- SQLite en `data/campaigns.sqlite`: personajes, mensajes, escenas, diario, objetivos, PNJ, hechos, incógnitas, consecuencias, FH, tablero y registro de resoluciones. Persistencia en disco del servidor, no solo memoria o almacenamiento del navegador.
- Varios jugadores por invitación y varios personajes por jugador. El servidor verifica propietarios; el anfitrión puede adjudicar y controlar adversarios. En un dispositivo compartido, el anfitrión selecciona el PJ que habla. Los jugadores con credenciales independientes usan navegadores o perfiles distintos.
- Estado compartido mediante consulta periódica cada 2,5 s. Versión optimista, exclusión mutua y transacción SQLite. Un identificador de acción ya confirmado no vuelve a tirar dados ni gastar recursos. Un estado antiguo produce un conflicto visible. Un envío interrumpido conserva el identificador para recuperarlo al recargar.
- Mensajes de acción, diálogo de PJ, fuera de personaje, notas privadas, narración de IA y reglas. Los secretos del anfitrión y las notas privadas se filtran en el servidor y no se envían a los demás jugadores ni al modelo.
- Ficha manual guiada: características, raza/clase/nivel, PG, CA, salvaciones, habilidades, dotes, ataques, inventario/carga, conjuros, recursos y condiciones. Totales declarados; no se presenta como generador reglamentariamente validado.
- Dados automáticos del servidor y físicos con validación de rango, modificadores declarados, origen y visibilidad. La tirada genérica no aplica consecuencias por sí sola.
- TREY: d10/d8/d6, probabilidades, límites 1–10, resultados excepcionales, detalle, eventos por dobles/triples originales, nueva tirada de evento, tabla posterior al giro, FH 2/3, evento voluntario una vez por escena, punto de giro y detención de nuevas FH. Gasto según tabla p.34 abre adjudicación manual; no cambia silenciosamente Pathfinder.
- Tablero 20×20, fichas de una casilla, zoom y desplazamiento por barras; recorrido previo, costes, muros, terreno difícil, iniciativa, rondas y turnos, movimiento limitado a la velocidad y una acción de movimiento automatizada. Resolución manual permite registrar costes estándar, movimiento, asalto completo, rápida o inmediata, PG, condiciones y recursos. Revisión de restricciones y excepciones sigue siendo humana.
- Tres originales accesibles con visor PDF nativo, página, búsqueda FTS5, búsqueda de índice, marcadores y enlaces de referencias. En móviles sin visor PDF nativo puede ser necesario abrir/descargar el original con el navegador.
- Exportación e importación JSON del anfitrión. Una importación sustituye el estado actual; reasigna los personajes al anfitrión y descarta notas privadas anteriores para no transferirlas a participantes equivocados. No exporta credenciales ni invitaciones.

## Fuentes verificadas

Se extrajeron **1.008 páginas** conservando libro y número de página del PDF:

| Libro | Páginas PDF | Identificación en el original |
|---|---:|---|
| Reglas básicas | 577 | Pathfinder 1e, Devir, depósito legal 2013; PDF p.3: erratas 1.4, equivalente a sexta reimpresión inglesa |
| Bestiario | 329 | Pathfinder 1e, Devir, depósito legal 2014; PDF p.3: erratas 2.0, equivalente a tercera reimpresión inglesa |
| TREY | 102 | v1.0; edición castellana 77Mundos 2026, PDF p.101 |

Se leyeron créditos, índices y procedimientos pertinentes; no se afirma una revisión exhaustiva de todo el contenido de los tres libros. Las páginas con poco texto están identificadas en `data/extraction-report.json`; parecen principalmente portadillas/ilustraciones y no se ha realizado una auditoría visual de todas ellas. No se ejecutó OCR: Tesseract no está disponible. Los textos extraídos no son una transcripción certificada de todas las tablas.

Reglas implementadas comprobadas en Reglas básicas: iniciativa, impresa p.178 / PDF p.179; movimiento, diagonales, ocupación y terreno difícil, impresa pp.192–193 / PDF pp.193–194. La iniciativa desempata por modificador total y luego azar. Una diagonal hacia terreno difícil cuesta tres casillas. Las tablas de TREY pp.19 y 23 se comprobaron visualmente contra el original.

Contradicción registrada: TREY p.25 llama «Objetivo en Curso» al d8=7; la tabla p.23 indica «Objetivo Final». Se usa la tabla. No se confunden dados originales con modificados al detectar eventos. Se impide repetir la misma pregunta normalizada, pero preguntas equivalentes expresadas con otras palabras necesitan revisión de lógica interna por el director.

Adaptación multijugador explícita: FH en una reserva común, decisiones por consenso y gasto con consentimiento unánime registrado por el anfitrión. Esto no es una votación autenticada de cada participante.

## Red e infraestructura

Las salas son compartidas **si todos acceden a esta misma instancia**. No se presentan como un servicio online ya publicado.

Para una red local de confianza:

```powershell
$env:HOST = '0.0.0.0'
python server.py
```

Los demás acceden a `http://IP-DEL-SERVIDOR:8787` y utilizan la invitación. El acceso puede requerir configuración de firewall. No se ha abierto ningún puerto del router ni modificado el firewall.

Para Internet faltan despliegue en un servidor persistente, HTTPS/proxy, gestión operativa de copias y controles de acceso adecuados a ese despliegue. `ThreadingHTTPServer` es el servidor de desarrollo, no la frontera pública de producción. No hay límite fijo de jugadores; el rendimiento depende del equipo, y actualmente las acciones se serializan en una única instancia. No se admite escalar a varios procesos de escritura con este bloqueo de memoria. El tablero tiene 400 casillas; no equivale a un límite recomendado de participantes.

Sites se consultó conforme a las instrucciones del entorno, pero las herramientas nativas de creación/publicación no estaban disponibles. No se ha registrado ni publicado un Site ni se ha generado una URL de Internet ficticia.

## Pendiente para cumplir el objetivo completo

1. Configurar y probar el director real con un modelo instalado; verificar una escena de principio a fin y calidad de consultas de reglas. El protocolo está integrado, su comportamiento narrativo no está certificado.
2. Completar validación de creación/progresión de personajes, CA de toque/desprevenido y desglose calculado de todos los modificadores; pregenerados verificados.
3. Completar herramientas TREY de palabras/misiones/clima, interpretación y cierre estructurado de consecuencias; interfaz del generador PNJ (el motor ya admite la acción `npc`). Control semántico de hechos repetidos. Interpretaciones automáticas todavía no confirman hechos estructurados.
4. Automatizar combate avanzado: ataques/críticos/daño, tamaño, alcance, AdO, cobertura, visibilidad, línea de efecto, áreas, duraciones, maniobras y capacidades; sorpresa/desprevenido; varios movimientos, pasos y excepciones. Actualmente se resuelven manualmente y se registran. No hay niebla de guerra ni tokens ocultos: no coloques secretos en el tablero público.
5. Preparación de encuentros con presupuesto PX/NMG y criaturas verificadas del Bestiario (Reglas PDF p.398); acompañantes/adaptación solitaria sin alterar estadísticas. La interfaz actual lo declara pendiente y permite añadir un acompañante como ficha manual.
6. Salida/revocación explícita de participantes, recuperación de credencial entre dispositivos, consenso autenticado por jugador, salas online de producción y pruebas de carga/reconexión bajo Internet real. «Salir» vuelve al inicio, no elimina la membresía.
7. Auditoría de tablas adicionales, OCR donde resulte necesario y mapa completo página impresa/PDF. Solo las correspondencias comprobadas se citan como tales.
8. QA visual/interactivo en navegador, tablet y móvil. No había una herramienta de control de navegador disponible; no se afirma haberla realizado.

## Validación

```powershell
python -m unittest test_engine test_server -v
node --check static/app.js
python -m py_compile server.py engine.py
```

Las pruebas cubren oráculo, dados originales, FH y giro, eventos, permisos de personajes, movimiento, PG/recursos asistidos, mensajes privados, identidad de varios jugadores, búsqueda de página, persistencia, importación/exportación, conflictos de versión y deduplicación HTTP. El adaptador narrativo usa una **respuesta de prueba solo dentro del test**, no se vende como prueba de una IA real. Otra prueba comprueba que la ausencia de IA no produzca una narración ficticia.

Para regenerar texto: `.deps` contiene las dependencias de extracción instaladas en el espacio de trabajo. `python extract_fast.py` usa PyMuPDF. El servidor ya dispone de los JSON extraídos y no necesita esas dependencias para ejecutarse. Mantén los manuales y la base de datos en almacenamiento privado.
