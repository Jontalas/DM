# Reanudar el desarrollo

Estado vigente: **8 de noviembre de2026**. Desarrollo activo sin dependencia del usuario. No parar tras un checkpoint, informe o despliegue: continuar trabajo autorizado. El usuario lo ratificó varias veces. No crear goal inferido ni subagentes sin instrucción aplicable.

## Directivas permanentes

AGENTS.md, PRODUCTO.md y USABILIDAD.md. Extrema sencillez: situación y decisiones pertinentes primero; detalles progresivos, teclado/tacto, ayuda local sin IA/escrituras. IA dirige ficción/PNJ; motor valida reglas/estado; jugador decide. Reglas básicas Pathfinder1e/Bestiario/TREY originales son autoridad del módulo; otros sistemas por paquetes, sin anunciar cobertura inexistente. Roll20 referencia funcional, sin afirmar observación directa ni equivalencia completa. Pregunta visual del usuario era curiosidad, no cambio de prioridades.

Autonomía para analizar, desarrollar, probar, documentar, respaldar/desplegar y verificar con Render/Firebase/Anthropic existentes. Ningún servicio/gasto recurrente nuevo. Mínimo IA/Firebase: cálculo/navegación/ayuda locales, no repetir inferencias ni administrar reglas a mano cuando motor pueda resolver. No tocar partidas personales. Los cuatro hitos de prueba personal de PRODUCTO.md siguen pendientes: no invitar por bloques parciales. Continuar sin esperar respuesta del usuario.

## Producción actual

- **ff8e8a59fe836f1a34a00ef01c8e401358d619e7**, Render **7631161921 success**. Rama feature/rule-pack-engine, main actualizado sin force. https://dm-cronicas.onrender.com. Revisión/salud HTTPS200 y descriptor1.9 comprobados.713 completas (176,454s); lectores de sesiones viaje/noche1.9 con EXPECTED_RELEASE correctos, cero acciones/inferencias nuevas. Decisiones preparadas publicadas, semántica real del nuevo campo aún no ensayada; simulación/HTTP documentados.
- **707 completas correctas sin omisiones (171,260s)**, .deps/director-travel-final-tests.log, sesión19729 terminada.36 afectadas y navegadores de declaración/creador/aventura/memoria/privacidad/rutas1.6 por paz/combate/regreso correctos. Sin cambios mecánicos posteriores al inicio de esa suite.
- Viaje por declaración real confirmado con una sola inferencia Haiku,5720ms cliente: patio→cobertizo; guardiana en patio, PG16/7, reloj/copia/duplicado conservados. Narración real revisada, sin decisiones extra del PJ. Navegador real de la misma campaña en lectura correcto, cero nuevas acciones/inferencias.

## Recorrido y límites publicados

Humano guerrero1 legal, patio nocturno iluminado por faroles, acuerdo/combate/auxilio/recuperación compartida acotados, noche opcional y ruta patio/cobertizo/almacén/regreso. Objetivo global persiste aunque quede búsqueda opcional. Hallazgos/posiciones/salud por escena; guardiana queda en patio. Versiones1.0–1.9 congeladas; solicitudes antiguas sin versión siguen1.0. BoardScenes filtra presentes para acciones/ocupación/flanqueo/iniciativa; pacientes remotos bloquean avances no cubiertos. No mapas gráficos, capas/visibilidad generales ni multijugador certificado.

Tregua1.8: guardiana original positiva herida ofrece cesar; PJ necesita Goblin elegido legalmente, turno propio del primer combate corto, PG no negativos, sin condiciones/correcciones/pendientes. Elegir aceptar conserva heridas/posiciones/acciones/reloj. Respuesta breve gratuita incluso a0; no Diplomacia ni decisión por el jugador. Recibo/mensaje/propietario/copia verificados. No añadir Común a la plantilla original: solo habla goblin.

Noche1.9/restScope3/recibo3: única noche elegida antes de investigar, PJ a0 con ligera puesta puede0→1PG, guardiana positiva herida permanece despierta sin curarse. Positivos conservan preparación normal de cota sin ayuda: quitar60s/dormir28800s/poner240s, total29100s; ligeras28800s. No preparación de armadura a0, negativos, fatiga, recursos diarios, condiciones/pacientes/efectos pendientes ni noches repetibles. Recibo3 vincula hash de tregua o None en acuerdo inicial; recibos1/2 y definiciones anteriores intactos. DESCANSO_PATHFINDER.md/TREGUA_PATHFINDER.md.

No inventar duración de viajes/búsquedas ni amanecer. Diario indica hora desconocida tras actividad no medida, conserva referencia original bajo detalle accesible. Viajes por declaración solo para acción inequívoca, propietario y salida pública disponible; pregunta/charla/ooc/apertura/continuación no viajan. Esquema routeTravel opcional/enum; una misma llamada de conversación interpreta, motor de rutas aplica y omite memoria anterior que sobrescriba destino. Botones siguen sin IA. Captura privada restaura sin proveedor ni ruta privada original; indicador derivado no altera clave pagada anterior. VIAJES_DECLARADOS.md. La intención semántica depende del modelo, no está garantizada por código.

## Trabajo local pendiente: ataque por declaración

**Regresión cerrada:**719 completas correctas sin omisiones (162,263s), .deps/director-combat-final-tests.log, sesión49616 terminada.23 afectadas y navegadores de ataque declarado, encuentro desde creador y decisiones preparadas correctos. Sin cambios mecánicos desde inicio de suite. Publicar y comprobar nueva revisión/salud y estado existente usando lectores viaje/noche1.9 con EXPECTED_RELEASE, cero POST/IA. Descriptor permanece1.9. No nuevo ensayo pagado. Después continuar trabajo autorizado, especialmente diálogo del recorrido por defecto y recuperación/planificador, sin alterar plantilla/versiones existentes ni detenerse por checkpoint. Los siguientes párrafos de suite en curso quedan históricos.

Decisiones preparadas del apartado inferior ya publicadas/verificadas. Ahora director_combat.py y campo meleeAttack opcional, solo PJ del encuentro/guardiana preparados y presentes, combate/turno/acción/distancia/condiciones/permisos válidos. No preguntas/charla/ooc ni otras operaciones combinadas. combat.attack_context factoriza exactamente preflight/totales anteriores para disponibilidad y ejecución, sin RNG/mutación; fuentes PDF180/179 y185/184 revisadas visualmente. Motor resuelve mismos dados/daño/acción/desenlace; IA no aporta cifras ni decide terminar turno. Semilla ActionRandomness ligada a la talk original conserva dados al fallar commit, captura conserva intención sin nueva IA. ATAQUES_DECLARADOS.md.

60 regresiones iniciales,32 de contrato/motor y23 con HTTP correctas. HTTP/Waitress/emulador usa dados reales, captura estado de commit fallido y compara fichas/tablero/desenlace/auditoría exactos tras cliente nuevo/reintento; sin segundo proveedor simulado, duplicado/copia/permiso atómicos. Navegador desde creador guiado: pregunta/charla inmóviles, ataque por teclado, acción gastada bloquea repetir, móvil/tacto/copia UI/recarga; proveedor/dados de navegador simulados. **Suite completa en curso49616**, .deps/director-combat-final-tests.log. No cambios mecánicos después de iniciarla. Esperar resultado/resolver fallos antes de publicar; después verificar sesiones existentes solo en lectura, sin nuevas inferencias ni repetir viaje. No hay bloqueo del usuario. Párrafos inferiores de decisiones preparadas son el bloque anterior, ya cerrado.

## Decisiones preparadas publicadas

director_prepared_decisions.py local añade selección de tregua, sueño con ligera, preparación explícita de cota y comienzo de investigación, reutilizando acciones existentes sin dados. preparedDecision opcional enumera únicamente opciones ahora legales. Una decisión por declaración; no encadenar tregua/descanso/investigación. Preparación de cota exige quitar/dormir/volver a equipar explícitamente; «quiero descansar» debe aclararse. No aplica memoria que anticipe consecuencias. Modelo no cambia PG/reloj por narración.

19 afectadas correctas con contrato, recuperación de captura, propietario, HTTP Waitress/emulador, fallo503/cliente nuevo/reintento sin segunda llamada/duplicado/copia;0→1PG/guardiana2 y cota29100s. Fixture HTTP inicialmente chocaba argumento kind del helper: renombrado parámetro del helper a action_type; no cambio de API. Navegador nuevo: personaje legal por API del creador, ataques orgánicos hasta0, preguntas/descanso ambiguo sin acción, aceptación/sueño/investigación separados, cota explícita, teclado/móvil/toque/copia UI/recarga. Proveedor simulado, no prueba semántica real.

**713 completas correctas sin omisiones (176,454s)**, .deps/director-prepared-decisions-final-tests.log, sesión80711 terminada. Navegadores de decisiones declaradas, viajes declarados y cuatro casos de armadura1.7 correctos. No cambios de motor posteriores al inicio; no despliegue local aún. Respaldar/publicar y verificar revisión/salud con lectores existentes y EXPECTED_RELEASE, sin nuevos POST ni IA; descriptor permanece1.9. No hace falta repetir inferencia real de viajes ni ejecutar otro ensayo pagado para cada campo: distinguir contrato/simulación del proveedor real cerrado. DECISIONES_DECLARADAS.md conserva alcance. Registrar/continuar después de publicar: intención de combate validada y recuperación/planificador general, sin saltar prioridades de PRODUCTO.md.

## Ensayos cerrados protegidos: NO REPETIR

Todos privados en .deps; contienen credenciales/exportaciones. Nunca imprimir ni subir a Git. No borrar/renombrar sesiones para repetir guiones. Reutilizar lectores sin POST con EXPECTED_RELEASE cuando proceda.

- director-travel-live-session.json verified: una inferencia real,5720ms, c7e75e5. verify_director_travel_live.py no repetir ni --resume; lector verify_director_travel_production_browser.cjs correcto. PG16/7, cobertizo, guardiana patio, copia/duplicado.
- pf-truce-night-live-session.json verified: cero IA,1.9/2d0dd12, Render7630962714 success. WinError5 temporal OneDrive al guardar checkpoint antes de importar; recuperación de misma campaña/nonce con resume_pf_truce_night_verification.py, sin repetir combate/descanso. No ejecutar original ni recuperación; conservar temporales. Lector verify_pf_truce_night_production_browser.cjs correcto.
- pf-ceasefire-live-session.json verified: cero IA,1.8/589c6f2, Render7630892971 success. Guardiana2, tregua/duplicado/copia/continuación. Lector correcto tras ajustar comparador por sceneId legítimo de ruta, sin repetir acciones.
- pf-armor-night-live-session.json verified: cero IA,1.7/d7f32d9, Render7629118813 success.29100/28800s, preparación normal, máximo/equipo/estadísticas/NPC/copia/continuación. Lector acepta EXPECTED_RELEASE.686 completas anteriores (241,029s).
- pf-return-live-session.json verified: cero IA,1.6/40e3dc0, Render7628758418 success. Objetivo global cumplido en cobertizo con búsqueda local pendiente; PG16/7. Lector acepta EXPECTED_RELEASE.679 completas anteriores (237,812s).
- pf-night-live-session.json verified: cero IA,1.5/6da0a52, Render7628572059 success;671 completas (218,501s). No repetir.
- pf-route-live-session.json verified:1.4, una solicitud real del director,9125ms; no repetir.
- pf-continuity-live-session.json verified:1.3, dos solicitudes reales; no repetir tampoco --resume-before-provider. No inventar precio/tokens no expuestos.

## Fuentes y límites pendientes

Originales Devir revisados visualmente: Reglas PDF190–192/folios189–191 (incapacidad/estabilización/consciencia/curación),151/150 y568/567 (armadura/fatiga),152/151 y154/153 (tablas6-6/6-7),179/178 (cuentas/asaltos),184/183 y189/188 (hablar gratuito). Bestiario goblin PDF167/166 tiene PG7, no6: original español incluye clase predilecta. No corregir por memoria inglesa. Fuentes/licencias en CATALOGO_PNJ.md y licenses. Imágenes privadas en .deps/book-pages. PDF Core original en Desktop; extracción data/reglas.json de una línea enorme: parsear y mostrar fragmentos, nunca Get-Content entero.

Recuperación negativa, asistencia, fatiga y eventos simultáneos necesitan planificador conjunto; no inventar prioridades reglamentarias ni inconsciencia=sueño. pf_rest.night_healing es cálculo más amplio que acciones jugables, no autoriza cobertura general. Mantener consciencia histórica tras corrección positiva de negativos, límites de épocas/care3 y participantes remotos. Discrepancia Curar:Int PDF93 frente a tabla/listas/Sab documentada; conservar Sab. Calendario exacto, recursos, recompensas, aventuras/campañas largas y cuatro hitos siguen pendientes.

## Entorno y comandos

PowerShell/Windows, .venv/Scripts/python.exe. Emulador127.0.0.1:8182 JavaPID46356, reglas correctas/demo-cronicas-tests, sesión43167. No reiniciar por timeout. FIRESTORE_EMULATOR_HOST=127.0.0.1:8182 y FIREBASE_PROJECT_ID=demo-cronicas-tests; precheck test_firebase.FirestoreEmulatorTests.test_direct_client_read_denied_by_firestore_rules. ResourceWarnings/NativeCommandError esperables: prevalecen final unittest/código. Startup si falta: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_emulator.ps1 -Port 8182; rechaza puerto ocupado y carga reglas, sin política permanente.

Chrome/Playwright .deps/browser-tests. Lectores reales con node --use-system-ca (Node sin flag falla CA; no desactivar TLS). .deps/inspect_dm_deployment.py muestra solo revisión/deployment/status sin credenciales. Git/red pueden requerir escalación técnica autorizada; mutaciones necesitan require_escalated. Push secuencial:

git -c http.sslBackend=openssl -c http.sslCAInfo=.deps/windows-ca.pem push origin feature/rule-pack-engine

git -c http.sslBackend=openssl -c http.sslCAInfo=.deps/windows-ca.pem push origin HEAD:main

No force ni secretos. Verificar revisión exacta/salud y misma sesión en lectura; no inferencia repetida por despliegue. CRLF local puede diferir de GitLF. rg -g '*.js' static, no static/*.js en PowerShell. Código multilineal privado por apply_patch, evitar quoting Python anidado y Unicode por tubería. Checkpoints privados con reintentos breves al reemplazar por bloqueo temporal OneDrive.

Vista secundaria http://127.0.0.1:8765, lanzador32504/servidor7764, ejemplo plan-3 simulado sin Firebase/Anthropic, Python anterior. No representa recorrido actual; no herramienta de pestaña IDE y no pedir configuración. Skills ya aplicadas: debug, regression-testing, root-cause-analysis, interface-design. Historial completo del punto anterior en HISTORIAL_REANUDAR_2026-11-08_TREGUA_DESCANSO_Y_DECLARACIONES.md y archivos previos; prevalece este estado con Git/producción comprobada.
