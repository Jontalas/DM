# Reanudar el desarrollo

Estado vigente: **8 de noviembre de2026**. Desarrollo activo, sin bloqueo del usuario ni prueba personal que solicitar. Continuar análisis, código, pruebas, documentación y despliegue sin esperar nueva orden tras una entrega. El usuario ratificó expresamente que cerrar un checkpoint no justifica parar. No crear goal inferido ni subagentes sin instrucción aplicable.

## Directivas permanentes

Extrema sencillez y orientación: situación/decisiones actuales primero, detalles bajo demanda y ayuda accesible por teclado/tacto. IA dirige ficción/PNJ; motor valida reglas/estado; jugadores deciden. Autoridad: AGENTS.md, PRODUCTO.md y USABILIDAD.md. Roll20 guía interacciones; originales Pathfinder1e/Bestiario/TREY fundamentan el módulo actual. Otros juegos por paquetes, sin anunciar cobertura inexistente.

Reutilizar Render/Firebase/Anthropic, mínimo coste y ningún servicio recurrente nuevo. Ayudas, consulta, cámara/medición y datos ya cargados no llaman IA ni escriben Firebase. No tocar partidas personales. Originales, credenciales, sesiones, diagnósticos y capturas permanecen privados en .deps, nunca Git. Pregunta visual del usuario era curiosidad: no cambiar prioridades a costa del producto. Hitos personales de PRODUCTO.md siguen pendientes; estas entregas no son invitaciones a probar.

## Producción y evidencia actuales

- main/producción: **40e3dc0fb82395719367406a713a78dd87871fce**, Render **7628758418 success**. Revisión exacta, descriptor1.6.0 y salud HTTPS200 comprobados. https://dm-cronicas.onrender.com. Rama feature/rule-pack-engine.
- **679 pruebas completas correctas sin omisiones (237,812s)**, .deps/pf-return-route-final-tests.log, sesión37025 terminada.32 afectadas previas correctas. Después del inicio de suite solo presentación JS de hora desconocida/referencia, verificada por navegador. No hay suite en curso.
- Navegadores nuevos por acuerdo/combate, regreso/objetivo persistente, copia/recarga, teclado/móvil; rutas1.4/genéricas y noche1.5 correctas. Fuente/fuentes/diferencias Roll20 en ESCENAS_TABLERO.md y COMPATIBILIDAD_ROLL20.md. No observación directa de una mesa Roll20.
- Base nocturna1.5 anterior:6da0a523db54160abcc16cfd42c8fc02c58eeeb1, Render7628572059 success;671 completas correctas (218,501s) y33 selectivas por textos/vistas derivadas. Errores iniciales de fixtures corregidos; no se ocultaron fallos.

## Recorrido1.6 publicado

Creador legal humano guerrero1, encuentro del patio al inicio de una noche iluminada por faroles, elección de acuerdo/combate y reglas/recuperación soportadas. Opcionalmente el propietario elige una noche segura8h antes de investigar:1PG/nivel hasta máximo; solo PJ positivo/armadura ligera y guardiana original sana/despierta o muerta, sin pacientes/condiciones/pendientes/relojes médicos de ningún participante. Un único descanso preparado y primer encuentro de hasta100 asaltos: límites temporales del motor, no reglas contra descansar. No gasta/devuelve recursos, no cura PNJ ni resucita. Recibo de pf_night_rest.py reproduce origen/cálculo/tiempo y liga un mensaje de auditoría; importación rechaza alteraciones/huérfanos. No es un controlador general de descanso ni de fatiga/negativos.

Ruta original patio→cobertizo opcional→almacén, con regreso almacén→patio incluso antes de terminar de buscar. Hallazgos, posiciones, terreno, salud, época y reloj conservados; guardiana queda en patio. `completion:{scene,requires}` es dato opcional de ruta: resultado global deriva de hallazgos actuales/archivados y permanece cumplido al cambiar de lugar, aunque quede una búsqueda local opcional. Se registra una sola finalización, sin FH por volver. Versiones1.0–1.5 intactas, solicitudes antiguas sin versión siguen1.0. Sin completion se mantiene el final terminal anterior. No exponer requisitos/pistas de escenas futuras en contexto público.

Tableros solo incluyen presentes para movimiento/ataque/ocupación/flanqueo/tácticas/iniciativa. Pacientes remotos bloquean antes de dados; ninguna transición omite su seguimiento. Recibo pfContinuation2 vincula ruta original, participantes y ámbitos; objetivo sustituido o guardiana trasladada se rechazan al copiar. No menús generales de páginas, grupos separados, mapas gráficos, capas ni visibilidad completos.

No se calcula duración de búsquedas/viajes ni se inventa amanecer. El diario muestra «Hora no registrada» tras actividad no medida que vuelve obsoleta una referencia inicial/de descanso; conserva el texto original en «Última referencia de tiempo» con teclado, sin alterar worldTime. Las reglas no se aplican por narración. El prompt distingue salidas disponibles de lugares visitados; no garantiza semánticamente cada frase ni reescribe narraciones históricas.

## Ensayos reales cerrados: NO REPETIR

- .deps/pf-return-live-session.json **verified**, ensayo técnico1.6 con **cero inferencias**. Salida antes de terminar/volver/objetivo, regreso al cobertizo con búsqueda local pendiente y objetivo global cumplido; PG16/7, PNJ en patio, reloj/duplicado/copia intactos. .deps/verify_pf_return_live.py se niega a repetir. No borrar/renombrar sesión.
- Navegador de esa misma campaña .deps/verify_pf_return_production_browser.cjs correcto: revisión/salud, recarga, foco de salida/diario/referencia temporal por teclado, móvil y **cero POST de acciones/nuevas inferencias**. Captura pf-return-production-mobile.png revisada. Usar node --use-system-ca; acepta EXPECTED_RELEASE para comprobar una revisión posterior sin modificar sesión ni jugar nuevas acciones.
- .deps/pf-night-live-session.json **verified**, ensayo técnico1.5 con cero IA: noche8h, máximo de PG, guardiana intacta, duplicados/copia/continuación correctos. Su navegador de lectura pasó en6da0a52. No repetir guion ni borrar sesión.
- .deps/pf-route-live-session.json **verified**, ensayo1.4 con una solicitud real del director (9.125ms cliente); PG16/7 y ruta/copia/posiciones conservadas. No repetir.
- .deps/pf-continuity-live-session.json **verified**, ensayo1.3 con dos solicitudes reales. No repetir guion ni --resume-before-provider. Tokens/precio no expuestos; no inventar estimación.
- Todas las sesiones son privadas y contienen credenciales/exportaciones. No imprimirlas ni publicarlas. Los ensayos nuevos no alteraron partidas personales. Ante fallos futuros recuperar la misma captura/acción sin nueva inferencia; no fabricar otra sesión para depurar.

## Trabajo local y siguiente paso inmediato

**Ajuste de presentación local ya probado, todavía sin publicar:** lista de personajes muestra Ha muerto/Moribundo/Inconsciente y estable/Incapacitado según PG/consciencia cargados; positivos sin rótulo extra. Usa las mismas condiciones de consciencia que la ficha, no cambia reglas ni estado. static/app.js y tres navegadores modificados. Pruebas orgánicas de regreso con PNJ muerto, auxilio moribundo→estable, recuperación compartida a0/negativos, armadura estable, muerte/copia/recarga/móvil correctas; capturas revisadas. No repetir679 por presentación. Documentado USABILIDAD.md/TRABAJO.md. Respaldar/publicar este ajuste y verificar revisión/salud/recurso; reutilizar navegador real de la misma sesión1.6 con EXPECTED_RELEASE, sin acciones ni IA.

Después continuar **recuperación avanzada y planificador conjunto**, fuentes/contrato en DESCANSO_PATHFINDER.md y RECUPERACION_PATHFINDER.md. `pf_rest.night_healing` admite cálculo aislado más amplio que la acción1.5/1.6; no confundirlo con una función jugable. Resolver consciencia, asistencia conocida, curación, armadura/fatiga y eventos coincidentes en el mismo intervalo, incluidos participantes remotos, con recibos reproducibles. No inventar prioridad general de sucesos ni equivalencia inconsciencia/sueño. Verificar originales antes de modificar una mecánica. Mantener fuera de catálogo cualquier base incompleta y seguir trabajo independiente sin pedir confirmaciones rutinarias.

No saltar barrera adventure.validate_start para mezclar campañas arbitrarias ni borrar encuentros al acabar una ruta. Calendario exacto, sucesos coincidentes, fatiga, descanso de pacientes negativos, recursos diarios, aventuras/campañas largas y los cuatro hitos siguen pendientes. Una narración, un número de pruebas o un despliegue saludable no certifican una aventura autónoma completa.

## Fuentes y límites que conservar

Originales Devir: Reglas PDF191–192/folios190–191,151/150 y568/567 revisados visualmente; tabla armaduras PDF152/151 y cuenta/asaltos PDF179/178 verificados. Percepción PDF101 y elegir10/20 PDF87 para búsquedas; sus CD son adjudicación original, no tabla oficial. Numeración de contexto TREY PDF/folio12 ya revisada: volver no concede FH. Bestiario goblin PDF167/166, permisos en CATALOGO_PNJ.md.

Conservar consciencia histórica tras correcciones positivas de negativos (recovery-state-2); una corrección no certifica asistencia ni curación reglamentaria. Curación hasta0 restaura consciencia según regla explícita PDF191. Reloj compartido actual resuelve cuentas coincidentes completas y se detiene conservadoramente antes de descanso no cubierto; límite del motor, no regla. Dormir con armadura intermedia/pesada requiere fatiga/día siguiente todavía no integrados. Discrepancia Curar:Int PDF93 frente a tabla/listas/Sab documentada, motor conserva Sab. FAQ1e403 y resultados2e descartados como evidencia.

## Entorno y comandos

PowerShell, .venv/Scripts/python.exe. Emulador **127.0.0.1:8182**, JavaPID46356 con firestore.rules y demo-cronicas-tests, sesión43167. No reiniciar por timeout ni detener procesos sin identificar. Si falta emulador adecuado: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_emulator.ps1 -Port 8182; rechaza puertos ocupados y siempre carga reglas, sin cambiar política permanente. FIREBASE.md. Pruebas: FIRESTORE_EMULATOR_HOST=127.0.0.1:8182, FIREBASE_PROJECT_ID=demo-cronicas-tests; precomprobar lectura sin autorización HTTP403. ResourceWarning puede figurar como NativeCommandError; prevalecen salida final/código unittest.

Playwright .deps/browser-tests, Chrome instalado. Vista secundaria http://127.0.0.1:8765, lanzador32504/servidor7764: ejemplo plan-3 con datos/director/dados simulados, sin Anthropic/Firebase, Python anterior. No representa la ruta real1.6. No herramienta de pestaña IDE; mantener enlace sin retrasar desarrollo ni pedir configuración.

Skills aplicadas: debug, regression-testing, root-cause-analysis, interface-design. Git/red pueden requerir escalación técnica; push/despliegue existentes autorizados:

git -c http.sslBackend=openssl -c http.sslCAInfo=.deps/windows-ca.pem push origin feature/rule-pack-engine

Después de validar: mismo comando push origin HEAD:main. Verificar revisión exacta/Render/salud; no repetir IA por despliegue. CRLF local puede diferir de LF remoto: comparar blob Git o normalizar. Leer UTF8 y rg -g '*.js' static; no glob PowerShell static/*.js. No pasar Unicode por tubería Python que lo convierta en interrogantes.

Historial previo completo en HISTORIAL_REANUDAR_2026-11-08_NOCHE_Y_REGRESO.md y archivos anteriores. Prevalece este punto junto con Git/producción comprobada; TRABAJO.md conserva secuencia. No hay dependencia imprescindible del usuario.
