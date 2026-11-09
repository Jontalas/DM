# Reanudar el desarrollo

Estado: 9 de noviembre de 2026. Desarrollo activo y sin dependencia imprescindible del usuario. Este archivo contiene el estado vigente; la cronología técnica está en TRABAJO.md. El punto anterior íntegro se conserva en Git, revisión 1c783e5dc229ed18918ca49e66c79293176fabd3:REANUDAR.md, y en sus documentos de referencia.

## Cómo continuar

Continuar autónomamente después de entregas y checkpoints; no pedir «continúa» ni pruebas personales rutinarias. No crear goals inferidos ni subagentes sin instrucción aplicable. AGENTS.md, PRODUCTO.md y USABILIDAD.md son autoridad.

El usuario teme un proyecto incontrolable y no entiende informes técnicos. Cerrar primero una aventura corta individual: entrada, personaje guiado, mesa/tablero/conversación, decisiones y reglas soportadas, IA, guardar/salir/reanudar/copia. No ampliar sistemas, clases ni casos mecánicos no bloqueantes. Cooperación de dos propietarios experimental. Mantener los objetivos finales; el recorte afecta a la primera entrega.

Comunicar qué puede hacer el jugador, qué falta y dónde verlo. No usar contadores de pruebas o commits como sustituto del avance del producto. Estimación de planificación provisional: 2–4 semanas efectivas y revisión visual en 3–5 jornadas; no fecha prometida ni estimación de la visión completa. Hito1 acotado alcanzado/notificado una vez; hitos2–4 pendientes. No invitar de nuevo por ajustes parciales.

Siguiente trabajo autorizado:

1. Publicar/verificar la consulta de personajes de otra escena yel aviso de salud inequívoco (bloque local abajo); mantener el informe local con capturas reales rotuladas.
2. Continuar la revisión de primeras decisiones, combate y recuperación del recorrido individual. Resolver fricciones observadas, conservando agencia y reglas; no expandir el alcance para producir más cambios.
3. Conservar el progreso en estos archivos existentes. No crear un MD por corrección: PRODUCTO para alcance, REANUDAR para continuidad, TRABAJO para detalle, USABILIDAD para criterios/evidencia.

## Producción y verificación actual

**00b3ae640983628c6fa173ffd6cd1273e1b03fdb**, Render **7653618090 success**, ambas ramas publicadas. Revisión, salud y character-creator.js/character-checks.js/tabletop.css exactos comprobados públicamente. Descriptor Pathfinder **1.15.0**. Incluye fichas de consulta ycontinuidad consolidada.

Motor desde **e174ea8ee0381f53b4953ac3b43e5db3b5fadce4**: **945 pruebas completas correctas, 300,506s**, .deps/copy-shape-final-suite.log, sesión21341 terminada. Ningún Python modificado después de ese arranque; cambios posteriores solo UI/pruebas/docs. No repetir suite completa sin cambio o preocupación concreta. No hay pruebas ni inferencias en curso.

Lectores reales de capítulos y clínica correctos sobre esa base; revisiones UI posteriores verificadas con .deps/verify_public_ui_release.cjs (release/salud/recursos contra Git, normaliza CRLF). Usa EXPECTED_RELEASE y VERIFY_UI_ASSETS. No lee campañas, ni envía POST o IA; /api/status mantiene tres lecturas existentes de metadatos de manuales y health su comprobación existente. Evitar releer campañas por cada cambio de presentación. Para cambios de estado, usar lectores protegidos con POST bloqueado y revisión exacta.

## Trabajo local listo para publicar

Grupo lateral: NPC consciente o muerto de otra escena se consulta bajo botón «En otra escena»; personaje jugador, pacientes inconscientes/moribundos ycondiciones siguen visibles. Reutiliza plantilla de fila yconsulta de ficha, sin cambiar datos, posiciones, visibilidad servidor oreglas. Popup/consulta porEnter ytacto no genera acciones. Salud de ficha identifica «Este PNJ», «Tu personaje» o«Este personaje» para evitar atribuir muerte delPNJ aljugador; cálculos intactos.

Ruta navegador1.6 acuerdo/combate/5pistas/3escenas/regreso/copia/móvil correcta; NPCremoto consultable, estado yubicación conservados. Casos defensivos de render solamente (moribundo/condición) permanecen visibles sin instalar pacientes imposibles enel estado. Clínica navegador correctacontextosaludpropio/corrección/copia/recarga. Capturas pf-route-return-parley-board-mobile yremote-npc-combat-mobile revisadas. Nodecheck/diffcheck correctos;945Python intacto. Publicar yverificar app.js,character-checks.js,tabletop.css. Después continuar revisión acotada del recorrido individual yactualizar informe local, no ampliar reglas.

## Qué está terminado en este bloque

- Entrada solo con nombre; idea opcional, ajustes de campaña plegados. Invitación prioriza unirse, limpia URL y restablece bienvenida. No se oculta la cobertura real.
- Personaje: nombre/estilo → revisión → confirmar, personalización completa opcional. Estilo elegido con texto/aria-pressed; herramientas de adversario/manual bajo avanzadas. Foco de teclado conservado. Fórmulas bajo demanda. Ficha recién creada enlaza con elegir aventura para anfitrión autorizado o volver a mesa para los demás.
- Elección: ejemplos preparados primero, descripciones públicas sin secretos y límites expresos de generación/adaptación. Patio individual experimental disponible solo en su ámbito original, consulta antes de entrar. Catálogo público cacheado en memoria por página, sin datos privados/Firebase, reintento tras fallo.
- Mesa: papel y controles verdes, fuentes locales, conversación más ancha, escena antes de acciones, ficha preparada plegada con contenido íntegro. Ayuda d20/10/20 local. Solicitud manual bajo excepciones. Preparación sin escena «Por decidir», atajo del patio compacto y presupuesto solo en combate. Cuadrícula aún provisional; sin mapas ilustrados, capas ni visión nueva.
- Fichas: consulta por defecto también para PNJ preparados, fuente/límites/licencias bajo demanda; corrección excepcional plegada/confirmada, manualOverride visible, causas de no editar/tirar explícitas.
- Copias: validación estructural antes de sustituir estado, sin recalcular/reparar fichas manuales. Rechaza tipos/IDs/turnos/mensajes dañados y números no finitos; conserva adaptadores y formatos legítimos comprobados. JSON ilegible se explica localmente; rechazo400 conserva partida y ofrece motivo plegado. Fallos de red mantienen recuperación de envío. Cambio de acceso durante lectura cancela importación y limpia avisos entre partidas. VALIDACION_COPIAS_PLAN.md.

Evidencia UI: opening (nombre solo, camino corto Enter/botón, enlace poscreación0API, ejemplo/ruta, ayuda local, copia, móvil), creator (personalización, presupuesto, invitado/adversario, teclado, único guardado), patio (selector/atajo, catálogo una vez, acuerdo/combate/auxilio), grupo (sin patio cooperativo, permisos/copias y capítulos simulados), biblioteca (JSON ilegible0envíos, rechazo/estado intacto/copia válida/cambio durante lectura), mesa (gestos/permisos/móvil0escrituras locales y un movimiento confirmado) correctos. Pruebas de proveedor simuladas, **ninguna IA real nueva en este bloque**. Detalle cronológico y fallos de guiones corregidos en TRABAJO.md.

## Vista de avances: conservar estado

Usuario confirmó acceso a **http://127.0.0.1:8766**. **No reiniciar ni resetear**: podría estar interactuando. Lanzador48700, .deps/preview_current.py, logs current-preview.log/current-preview-error.log. TestStore en memoria, Aria legal y apertura escrita, director no conectado, sin Firebase/Anthropic. Backend cargado anterior; assets actuales se leen dinámicamente. No presentar la demo como prueba de todos los cambios recientes del servidor.

**http://127.0.0.1:8766/avance-local.html**, estático ignorado, generador .deps/build_progress_page.py. No se despliega. Capturas incrustadas, alcance/plazos/tamaño; consulta0API/POST/externos, teclado/móvil comprobados con check_progress_page.cjs. Demo en lectura con check_current_preview.cjs, POST bloqueados y versión intacta. No hay herramienta de pestaña IDE; no pedir configuración. Vista vieja8765 (32504/7764) secundaria, no preferida.

Capturas revisadas: table-presentation-before, current-preview-desktop/mobile, entry-simplified-mobile, entry-invitation-desktop, adventure-choice-example/route-mobile, first-character-step-mobile, creator-concept-mobile, creator-quick-review-mobile, ready-to-choose-adventure-mobile, copy-rejected-current-game-mobile. Todas en .deps. Distinguir prueba local/demostración/director simulado de producción.

Auditoría de7516f1c en .deps/project-size-audit.json:107archivos propios/954468bytes/12041líneas;201pruebas,84docs,202recursos externos por separado. .deps1,57GB,873,8MB de imágenes de manuales. No confundir ese material con aplicación ni borrar originales/evidencias. Este bloque reutilizó archivos de app/pruebas/docs existentes, sin dependencia nueva.

## Límites y referencias técnicas que se conservan

Core/Bestiario/TREY originales mandan; verificar apartado/tablas/excepciones y PDF antes de cambiar mecánicas. IA dirige ficción/PNJ, motor reglas/estado, jugador decisiones. Render/Firebase/Anthropic existentes autorizados; sin nuevo gasto recurrente, servicios ni campañas personales. Interacciones/ayudas locales sin IA/escrituras. Seguridad, privacidad, reglas y persistencia preservadas.

Patio PF1.0–1.15 congelado; API sin versión sigue1.0, frontend solicita descriptor1.15. Humano guerrero1, guardiana variante6PG/CA15/Con10/Int12/Común+goblin; original7PG/CA16/Int10/goblin intacto (hash04f7b0f12f49dc360411d4aae8e54a3c19a82bce6e465b5d267ffdf9368fda12). CATALOGO_PNJ.md ylicencias. No imponer recuerdo inglés al original español.

EXPLORACION_INCAPACITADO.md, EXPLORACION_CONSCIENTE.md, MOVIMIENTO_INCAPACITADO.md, AUXILIO_PNJ.md, TREGUA_INCAPACITADO.md, ESPERA_GUARDIANA.md, DESCANSO_PATHFINDER.md yTREGUA_PATHFINDER.md contienen cobertura médica/recibos. Negativos conscientes solo con prueba actual reproducida de ambos pacientes; no omitir pacientes remotos, no inconsciencia=sueño. Velocidad reducida afecta presupuesto, no velocidad normal guardada. Ataque incapacitado cuesta1PG; sin curación/tiempo inventados. Curar usa Sab, discrepancia cabecera Int PDF93 documentada. **pf_npc_aid debe actualizar tablero en sitio**: controlador automático conserva referencia; sustituirlo puede ejecutar turno extra. Planificador general, fatiga/recursos/recompensas y campañas largas pendientes.

CAPTURA_POR_ENVIO.md, CONTEXTO_TABLEROS.md, EVOLUCION_MEDICA.md: acción/actor/body/version vinculados a captura; conservar contexto y claves originales, no repetir proveedor tras fallo de commit ni reescribir narración. Memoria/proyección completa en captura y acotada al modelo, sin sombrear world_view. MEMORIA_DEL_MUNDO.md, MEMORIA_COMPACTA.md yCONTEXTO_MEMORIA_MUNDO.md contienen sus contratos. CAPITULOS_AVENTURA.md, CAPITULOS_COMPARTIDOS.md yAPERTURA_PREPARADA.md: mismo lugar,8capítulos/192000bytes, originales privados íntegros, doble consentimiento propietario exacto, propuesta pendiente descartada en copia, apertura escrita0IA. No certifica campaña abierta o cooperación general.

Originales revisados: CorePDF87/folio86 y101/100 (búsquedas);190–192/189–191 (clínica);151/150 y568/567 (armadura/fatiga);152/151 y154/153 (tablas6-6/6-7);179/178 (iniciativa);184/183 y189/188 (hablar). Bestiario167/166 goblin. Imágenes .deps/book-pages; PDF Core Desktop. data/reglas.json es una línea enorme: parsear fragmentos, nunca volcar entero. Diagnóstico viejo .deps/test_campaign_copy_shape_pending.py queda fuera de suite yno debe reactivarse: casos limpios ya integrados en test_campaign_copy_ownership_http.py.

## Partidas y ensayos protegidos: no repetir productores

Todos los JSON de sesión en .deps son privados, con credenciales/exportaciones. **No imprimir/subir a Git, borrar/renombrar para repetir ni ejecutar productores live, finishers o resumes cerrados.** Solo lectores protegidos cuando corresponda, con EXPECTED_RELEASE; no repetir inferencias por despliegue.

- **hito1-invitation-session.json** prepared/notifiedtrue,0IA: invitación opcional ya comunicada una vez. No ejecutar prepare_hito1_invitation.py, no asumir vacía ni tocarla.
- **chapter-continuity-live-session.json** verified/simulatedfalse/directorRequests1,18175ms. GUI/asistente → apertura0IA → investigar/salir/cerrar/reanudar → segundo capítulo con una IA → investigar/copia. Gaspar/carta/agencia/secretos passed-scoped. No recoger/abrir/entregar carta por localizarla. CONTINUIDAD_REAL_2CAPITULOS.md. No verify_chapter_continuity_live.cjs. Lector verify_chapter_continuity_production_browser.cjs. Locales52284/63508 simuladas no son prueba real; imagen real-narration es extracción de texto público, no screenshot literal.
- **npc-aid-dialogue-live-session.json** verified,1IA11222ms, passed-scoped: PJ−2 consciente/NPC6, dos Curar fallidos, estabilización natural/recuperación no asistida, permiso público respetado. Setup legal API con un fallo físico natural1 tras atasco del productor a0PG/60turnos; no fullGUI/dadosPCservidor. No productor verify_npc_aid_dialogue_live.py ni finish_npc_aid_dialogue_live.py. Lectores production/resume solo lectura.
- **combat-investigation-live-session.json** verified,1IA6183ms: PJ12/NPC−2 despierta,5pistas/3escenas/regreso/copia. No verify_combat_investigation_live.cjs. Lectores producción/reanudación.
- **dialogue-investigation-live-session.json** verified técnico, **semanticReview.failed**,1IA9440ms: inventó condición para acceso ya permitido. Conservar fallo histórico, no certificarlo ni repararlo. No verify_dialogue_investigation_live.cjs. Corrección posterior/ensayo clínico no reescribe esa historia.
- **npc-wait-live-session.json** verified0IA/42622b8,1h asistida/PJ16/NPC−2. No verify_npc_wait_live.py.
- **declared-investigation-live-session.json** verified1IA8199ms/3e6f4ef,5pistas/3escenas/copia. No verify_declared_investigation_live.cjs ni finish_declared_investigation_verification.cjs.
- **common-guard-live-session.json** verified0IA/065e63f,1/6PG,Común,noche/ruta/copia. No verify_common_guard_live.py.
- **director-travel-live-session.json** verified1IA5720ms/c7e75e5. No productor ni --resume.
- **pf-truce-night-live-session.json** verified0IA/2d0dd12: WinError5 OneDrive recuperado en misma campaña/nonce, sin repetir combate/descanso. No productor ni resume_pf_truce_night_verification.py; conservar temporales.
- **pf-ceasefire-live-session.json**, **pf-armor-night-live-session.json**, **pf-return-live-session.json**, **pf-night-live-session.json** verified0IA; no repetir.
- **pf-route-live-session.json** verified1IA9125ms/1.4 y **pf-continuity-live-session.json** verified2IA/1.3: no repetir ni --resume-before-provider.
- **rule-director-live-session.json** histórico protegido; no repetir productores/conversiones. Antes de tocarlo consultar historial y estado del JSON sin imprimir secretos.

## Entorno y comandos

PowerShell/Windows, .venv/Scripts/python.exe, Chrome C:/Program Files/Google/Chrome/Application/chrome.exe, Playwright .deps/browser-tests/node_modules/playwright. Emulador127.0.0.1:8182, demo-cronicas-tests, Java46356/sesión43167 históricos; comprobar antes de usar, no reiniciar por lentitud. Entorno por comando: FIRESTORE_EMULATOR_HOST yFIREBASE_PROJECT_ID. Reglas cliente denegadas. ResourceWarnings/NativeCommandError/Win10038 de cierre conocidos: prevalecen resultado unittest y exitcode. Startup solo si falta: scripts/test_emulator.ps1 -Port 8182.

Navegadores de prueba lanzan test_browser_fixture.py con TestStore/proveedor simulado, sin claves reales. Producción Node --use-system-ca, nunca desactivar TLS. .deps/inspect_dm_deployment.py consulta solo metadatos de GitHub/Render sin imprimir secretos. .deps/verify_public_ui_release.cjs compara recursos del SHA indicado con Git, no el working tree.

Git/red/procesos pueden necesitar require_escalated, autorización existente. Añadir archivos explícitos, nunca .deps/secretos ni gitaddall. Push secuencial a feature/rule-pack-engine yluego HEAD:main, sinforce, usando -c http.sslBackend=openssl -c http.sslCAInfo=.deps/windows-ca.pem. main activa Render; esperar success yverificar SHA/salud/recursos. No repetir productor real para verificar.

Usar rg --files/rg -g '*.js' static, no comodines de ruta de PowerShell. Código multilineal/Unicode por apply_patch o archivo privado, no tubería que convierta acentos a?. No comandos destructivos combinando shells. Checkpoints privados con reintentos breves por OneDrive. Skills ya aplicadas: debug, regression-testing, root-cause-analysis, interface-design. Históricos HISTORIAL_REANUDAR_2026-11-08_EXPLORACION_Y_ENSAYOS.md yHISTORIAL_REANUDAR_2026-11-08_TREGUA_DESCANSO_Y_DECLARACIONES.md; estado de este archivo y Git comprobado prevalece.
