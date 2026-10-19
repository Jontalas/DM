# Crónicas · mesa de rol en español

Aplicación cliente/servidor para Pathfinder **primera edición** y TREY, con **Cloud Firestore**, **Firebase Storage** y **Claude Haiku**. Esta entrega es una base funcional ampliable; **no completa todas las etapas solicitadas**. No contiene una aventura de respuestas prefijadas ni un director simulado.

## Alojar en Render

Incluye un Blueprint [`render.yaml`](render.yaml) y un servidor de producción Waitress. Sigue [RENDER.md](RENDER.md) para desplegar desde GitHub y [FIREBASE.md](FIREBASE.md) para configurar bases, libros y Claude. Render no necesita disco persistente: los datos viven en Firebase. No se ha desplegado automáticamente.

## Iniciar

Requiere Python 3.11 o posterior, las dependencias de `requirements.txt` y Firebase configurado según [FIREBASE.md](FIREBASE.md). Render usa Python 3.13; las pruebas locales se ejecutaron con Python 3.14. Si faltan credenciales no se crea una base local como sustituto.

```powershell
cd C:\Users\Jonta\OneDrive\Proyectos\DM
python -m pip install -r requirements.txt
# Configura las variables Firebase y Anthropic; consulta .env.example.
python server.py
```

Abre **http://127.0.0.1:8787**. También puedes ejecutar `start.ps1`. Los originales se sirven desde Firebase Storage; para desarrollo sin bucket se permite leerlos del Escritorio con `BOOKS_DIR`. Las bases y las búsquedas siempre utilizan Firestore.

## Director de IA real

La IA que escribió esta aplicación no es el servicio de IA que dirige las partidas. El director usa Claude Haiku mediante la API de Anthropic. El recorrido conversacional con credenciales reales **no ha podido verificarse**.

Antes de arrancar el servidor, además de configurar Firebase:

```powershell
$env:ANTHROPIC_API_KEY = 'tu-clave-privada'
$env:ANTHROPIC_MODEL = 'claude-haiku-5-5'
python server.py
```

Integración real mediante [Messages de Anthropic](https://platform.claude.com/docs/en/api/messages/create), contexto recuperado y salida JSON con esquema. La configuración reside en el servidor. Las llamadas requieren acceso, crédito y conexión a Anthropic. No se ha realizado ninguna inferencia facturable con una cuenta real en esta sesión.

Si falta el modelo o falla el proveedor, el envío devuelve un error visible y no añade un turno falso. Puedes desmarcar «Responder con IA» para preparar personajes, conversar entre personas, tirar dados y usar los manuales. Eso es un modo de mesa asistida, no una partida dirigida por IA.

La respuesta narrativa puede proponer resoluciones pendientes, pero no modifica fichas ni tira dados por texto. El anfitrión valida cambios mediante el motor. Las respuestas sobre reglas muestran los fragmentos y páginas recuperados; su corrección semántica sigue dependiendo del modelo y de la revisión humana. No se envían los libros enteros en cada turno.

## Funciones disponibles

- Campaña con tono, límites de contenido, objetivo y dificultad declarada; continuación mediante credencial guardada en el navegador.
- Cloud Firestore: personajes, mensajes, escenas, diario, objetivos, PNJ, hechos, incógnitas, consecuencias, FH, tablero y registro de resoluciones. Persistencia remota, independiente del sistema de archivos de Render. Los PDF originales se guardan en Firebase Storage.
- Varios jugadores por invitación y varios personajes por jugador. El servidor verifica propietarios; el anfitrión puede adjudicar y controlar adversarios. En un dispositivo compartido, el anfitrión selecciona el PJ que habla. Los jugadores con credenciales independientes usan navegadores o perfiles distintos.
- Estado compartido mediante consulta periódica cada 2,5 s y control de versión. Firestore confirma atómicamente el estado, la versión y el marcador de acción. Un identificador ya confirmado no vuelve a tirar dados, gastar recursos ni solicitar narración. Un envío interrumpido conserva el identificador para recuperarlo al recargar. Una respuesta sin cambios evita descargar otra vez el estado; las consultas siguen produciendo lecturas a Firebase.
- Mensajes de acción, diálogo de PJ, fuera de personaje, notas privadas, narración de IA y reglas. Los secretos del anfitrión y las notas privadas se filtran en el servidor y no se envían a los demás jugadores ni al modelo.
- Ficha manual guiada: características, raza/clase/nivel, PG, CA, salvaciones, habilidades, dotes, ataques, inventario/carga, conjuros, recursos y condiciones. Totales declarados; no se presenta como generador reglamentariamente validado.
- Dados automáticos del servidor y físicos con validación de rango, modificadores declarados, origen y visibilidad. La tirada genérica no aplica consecuencias por sí sola.
- TREY: d10/d8/d6, probabilidades, límites 1–10, resultados excepcionales, detalle, eventos por dobles/triples originales, nueva tirada de evento, tabla posterior al giro, FH 2/3, evento voluntario una vez por escena, punto de giro y detención de nuevas FH. Gasto según tabla p.34 abre adjudicación manual; no cambia silenciosamente Pathfinder.
- Tablero 20×20, fichas de una casilla, zoom y desplazamiento por barras; recorrido previo, costes, muros, terreno difícil, iniciativa, rondas y turnos, movimiento limitado a la velocidad y una acción de movimiento automatizada. Resolución manual permite registrar costes estándar, movimiento, asalto completo, rápida o inmediata, PG, condiciones y recursos. Revisión de restricciones y excepciones sigue siendo humana.
- Tres originales accesibles tras instalarlos en Firebase: visor PDF nativo, páginas, búsqueda por términos normalizados en Firestore, búsqueda de índice, marcadores y enlaces de referencias. No es una búsqueda semántica ni una función nativa de texto completo. En móviles sin visor PDF nativo puede ser necesario abrir/descargar el original con el navegador.
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

Para Internet se proporciona la configuración de Render y el servidor de producción `python serve.py`, con Waitress. El despliegue real, la conexión de IA, los manuales y la gestión de copias deben configurarse como explica [RENDER.md](RENDER.md). `ThreadingHTTPServer` sigue siendo el servidor de desarrollo de `python server.py`. No hay límite fijo de jugadores; el rendimiento depende del equipo, y actualmente las acciones se serializan en una única instancia. No se admite escalar a varios procesos de escritura con este bloqueo de memoria. El tablero tiene 400 casillas; no equivale a un límite recomendado de participantes.

Sites se consultó conforme a las instrucciones del entorno, pero las herramientas nativas de creación/publicación no estaban disponibles. No se ha registrado ni publicado un Site ni se ha generado una URL de Internet ficticia.

## Pendiente para cumplir el objetivo completo

1. Configurar las credenciales reales de Firebase/Anthropic y probar una escena con Haiku de principio a fin. El protocolo y las transacciones están integrados y probados con emulador; el comportamiento narrativo del modelo real no está certificado.
2. Completar validación de creación/progresión de personajes, CA de toque/desprevenido y desglose calculado de todos los modificadores; pregenerados verificados.
3. Completar herramientas TREY de palabras/misiones/clima, interpretación y cierre estructurado de consecuencias; interfaz del generador PNJ (el motor ya admite la acción `npc`). Control semántico de hechos repetidos. Interpretaciones automáticas todavía no confirman hechos estructurados.
4. Automatizar combate avanzado: ataques/críticos/daño, tamaño, alcance, AdO, cobertura, visibilidad, línea de efecto, áreas, duraciones, maniobras y capacidades; sorpresa/desprevenido; varios movimientos, pasos y excepciones. Actualmente se resuelven manualmente y se registran. No hay niebla de guerra ni tokens ocultos: no coloques secretos en el tablero público.
5. Preparación de encuentros con presupuesto PX/NMG y criaturas verificadas del Bestiario (Reglas PDF p.398); acompañantes/adaptación solitaria sin alterar estadísticas. La interfaz actual lo declara pendiente y permite añadir un acompañante como ficha manual.
6. Salida/revocación explícita de participantes, recuperación de credencial entre dispositivos, consenso autenticado por jugador, salas online de producción y pruebas de carga/reconexión bajo Internet real. «Salir» vuelve al inicio, no elimina la membresía.
7. Auditoría de tablas adicionales, OCR donde resulte necesario y mapa completo página impresa/PDF. Solo las correspondencias comprobadas se citan como tales.
8. QA visual/interactivo en navegador, tablet y móvil. No había una herramienta de control de navegador disponible; no se afirma haberla realizado.

## Validación

```powershell
python -m pip install -r requirements.txt
python -m unittest test_engine test_server test_render test_firebase test_migration -v
node --check static/app.js
python -m py_compile server.py engine.py
```

Las pruebas cubren oráculo, dados originales, FH y giro, eventos, permisos de personajes, movimiento, PG/recursos asistidos, mensajes privados, identidad de varios jugadores, búsqueda de página, persistencia, importación/exportación, conflictos de versión y deduplicación HTTP. El adaptador narrativo usa una **respuesta de prueba solo dentro del test**, no se vende como prueba de una IA real. Otra prueba comprueba que la ausencia de IA no produzca una narración ficticia.

Para regenerar texto: `python extract_fast.py` usa PyMuPDF. Los JSON extraídos existen localmente, pero no se incluyen en Git: en un clon nuevo debes generarlos y cargarlos con `scripts/firebase_books.py`, según [FIREBASE.md](FIREBASE.md). El servidor puede arrancar con Firebase conectado y sin manuales: mostrará cero páginas indexadas. El límite operativo de campaña, las pruebas con emulador, el coste de consultas y la migración de SQLite están documentados en esa guía.
