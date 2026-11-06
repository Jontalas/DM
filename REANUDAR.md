# Reanudar el desarrollo

Estado vigente del **6 de noviembre de 2026**. Leer AGENTS.md, PRODUCTO.md y este archivo. El usuario ha reanudado el desarrollo y ratifica **continuar sin parar**, solicitando intervención solo ante una dependencia imprescindible. No hay bloqueo actual ni pruebas personales que pedir. No crear un goal inferido ni repetir ensayos remotos para obtener un éxito narrativo.

## Directiva nueva: sencillez extrema

Aplicación extremadamente fácil de usar: pantallas claras, sin abrumar con información u opciones, y orientación continua mediante ayuda contextual, tooltips accesibles o uso guiado. Incorporada a AGENTS.md y PRODUCTO.md; USABILIDAD.md recoge criterios y revisión pendiente. Aplicarla a funciones nuevas y existentes. Ayudas locales, sin IA ni operaciones remotas al consultarlas.

## Repositorio y producción

- Trabajo en `feature/rule-pack-engine`.
- Feature/main publicadas en **2d2f1ebc53e0ca80e34df4fb00e04afeb4002c97**. Render **7604965260 success**, revisión exacta en /api/status y /healthz HTTPS200 comprobadas. URL https://dm-cronicas.onrender.com. Incluye registro de asistencia y primera simplificación del encuentro/compositor; recuperación horaria aún no jugable.
- Esa revisión incluye El patio del peaje: entrada desde creador, PNJ preparado, acuerdo o combate por decisión propia, iniciativa/ataques automáticos, primeros auxilios, espera y estabilización/muerte, desenlace de derrota y copia. Fuentes/límites en ENCUENTROS_PATHFINDER.md. No es todavía una aventura autónoma completa.
- Verificación: **574 pruebas completas sin omisiones (127,479s)**, `.deps/pf-encounter-release-final-tests.log`; navegador acuerdo/combate/auxilio/cierre/móvil correcto. Descriptor público exacto comprobado en producción, sin IA ni escrituras de campaña. Ninguna partida personal modificada.
- Capturador Pathfinder previo incluido:3168478, Render7603193106 success,553 pruebas y siete posteriores. No repetir su integración ni los guiones reales de dados/PNJ anteriores.

## Último bloque cerrado y verificado

Registro de asistencia y primera simplificación siguientes ya desplegados en2d2f1eb. Sus menciones a estado local describen el desarrollo previo. La implementación horaria sigue pendiente.

**Registro de asistencia y cálculo de recuperación**, aún sin desplegar: `pf_recovery.py`, `test_pf_recovery.py`, RECUPERACION_PATHFINDER.md; modificaciones en engine/combat/pf_encounters/server y pruebas. `recoveryCare` se registra al estabilizar por iniciativa (sin ayuda) o primeros auxilios efectivos (con ayuda). Daño nuevo o corrección excepcional de PG lo retira. Importación valida el registro; copias antiguas conservan dato desconocido. Cálculo puro de consciencia por hora, sin curar PG, sin acción horaria ni reloj integrado todavía.

Fuentes originales vistas: Reglas básicas PDF190/folio189,191/190 y192/191. Constitución CD10 con penalizador de PG negativos;20 natural éxito,1 natural no es fallo automático. Con ayuda, fallar no resta PG; sin ayuda pierde1PG y puede morir. Consciencia y curación natural son procesos distintos. No ofrecer recuperación jugable antes de representar consciencia negativa, tiempo compartido, conducta de PNJ y persistencia de todos los afectados.

**581 pruebas completas con emulador correctas, sin omisiones (116,361s)**; `.deps/pf-care-record-final-tests.log`, sesión17128 terminada.38 afectadas correctas antes; seis pruebas del cálculo/registro y quince del encuentro. HTTP/Waitress conservan auxilio tras fallo de commit/cliente nuevo, ambos estados, derrota, duplicado y copia. Cero inferencias reales nuevas.

**Primera aplicación de la directiva de sencillez**, también local: AGENTS.md/PRODUCTO.md/USABILIDAD.md; encuentro con situación y decisiones primero, límites bajo ayuda desplegable, instrucciones de auxilio claras, riesgos necesarios visibles y motivos de indisponibilidad. Dados rápidos del compositor bajo «Tirar un dado», con explicación de tirada libre. Mantener ids/acciones/permisos y automatización. Navegadores `test_pf_encounter_browser.cjs` y `test_browser.cjs` correctos: ayudas cerradas inicialmente, apertura con teclado y tacto, ninguna acción al consultar, dados rápidos, tablero/chat y móvil. No se ha certificado toda la usabilidad.

## Próximos pasos concretos

**Estado posterior vigente:** bienvenida desplegada en **7f4833cb36dec2c357a2e44d017d527467283163**, Render7605123263 success, revisión exacta y salud HTTPS200. Nuevo bloque local: guía de turno/selección/acciones, ataques con motivo de indisponibilidad y alcance local, herramientas excepcionales bajo demanda y botones de recorrido pertinentes. Cuatro navegadores correctos (mesa general, encuentro con movimiento/acercamiento real, gestos, creador); motor sigue581 pruebas. Documentado en USABILIDAD.md/MESA_VIRTUAL.md/TRABAJO.md. Respaldar/desplegar este ajuste y continuar recuperación y continuidad, sin pedir nueva orden.

**Nuevo bloque local posterior a2d2f1eb:** bienvenida simplificada en static/index.html/app.js: ajustes opcionales plegados, ejemplo de premisa, límites claros e invitación contextual. El enlace de invitación abre el formulario; después de entrar se elimina ese parámetro para restaurar correctamente al recargar. Prueba de dos jugadores reprodujo el fallo anterior y ahora pasa; comprueba teclado sin POST y valores de opciones preservados. Biblioteca, regla-paquete, Cairn experimental y encuentro correctos con el nuevo inicio. Captura móvil y cierre de documentación antes de respaldar/desplegar esta mejora. No se cambia motor desde las581 pruebas.

Verificación del segundo bloque cerrada: captura móvil revisada sin desbordamiento; biblioteca vacía plegada y existentes abiertas automáticamente, restauración desde archivo correcta tras abrir sección. Navegadores de mesa general/biblioteca/paquetes repetidos tras el último ajuste y correctos. No hay pruebas en curso. Respaldar/desplegar esta bienvenida y verificar revisión/salud; continuar con recuperación y guía de mesa.

Los cuatro navegadores afectados ya han pasado: encuentro (teclado/tacto/ayudas), mesa general (dados rápidos/dos jugadores/tablero-chat/móvil), aventura Pathfinder y plan-3. Código del motor sigue siendo el de las581 pruebas correctas. No hay pruebas en curso. Cerrar respaldo/despliegue del bloque local y continuar con los puntos siguientes.

1. Revisar git status/diff y conservar el trabajo local anterior. Terminar documentación, comprobar navegadores afectados por el compositor, respaldar feature y desplegar únicamente el bloque verificado. Comprobar Render/revisión exacta/salud; no gastar inferencias para cambios deterministas o de presentación.
2. Recuperación: separar consciencia de PG antes de aplicar la prueba horaria. Revisar conjuntamente ataques/movimiento/acciones de incapacitado, turnos/tácticas, interfaz y copia. No asumir ayuda cuando falta registro. Reloj compartido y todos los pacientes en una acción duradera; probar fallo de commit/cliente nuevo/duplicado/permisos. Contrato en RECUPERACION_PATHFINDER.md.
3. Continuidad del encuentro y siguiente escena, retirada, consecuencias/recompensas verificadas. Mantener agencia y alternativas; la prosa no cambia estado. La definición1.0.0 desplegada está fijada: futuras versiones deben conservarla para copias, no editarla silenciosamente.
4. Revisar claridad del resto de la aplicación según USABILIDAD.md: bienvenida/entrada, ayudas pertinentes y herramientas avanzadas. No convertir la guía en administración mecánica ni saturación adicional.

## Método y límites

- Continuar análisis, desarrollo, pruebas, documentación y despliegue sin pedir «continúa». Una entrega no termina el trabajo. Intervención solo si imprescindible; seguir lo independiente. No prometer procesos inexistentes.
- Reutilizar Render/Firebase/Anthropic. Sin nuevos gastos recurrentes. Cálculo determinista primero; cero IA para ayuda, navegación, administración o cálculos. Agrupar consecuencias y evitar operaciones remotas redundantes.
- Consultar originales antes de cambiar reglas; página PDF y folio solo si comprobado. Curar: PDF93 encabeza Int pero tabla4-3 PDF90/listas/Sabiduría dicen Sab; se conserva el total Sab del creador y se documenta discrepancia sin atribuir errata oficial. No inventar curación, material ni reglas de otro sistema.
- No modificar partidas personales ni imprimir tokens/exportaciones completas. Evidencias y originales privados en .deps, fuera de Git. No repetir guiones privados de producción existentes ni inferencias narrativas fallidas.
- Pruebas por impacto; suite completa al cerrar motor. Simulación y proveedor real se documentan por separado. Los cuatro hitos de PRODUCTO.md siguen pendientes; no invitar por entregas parciales.
- No subagentes sin petición explícita aplicable. Skills ya usadas: debug, regression-testing, root-cause-analysis e interface-design.

## Entorno local

PowerShell, Python `.venv/Scripts/python.exe`, Node/Playwright en .deps/browser-tests, Chrome instalado. Emulador Firestore127.0.0.1:8181, Java PID42040 iniciado al reanudar; antes estaba caído. Pruebas con FIRESTORE_EMULATOR_HOST=127.0.0.1:8181 y FIREBASE_PROJECT_ID=demo-cronicas-tests. Comprobar identidad antes de terminar procesos; no reiniciar por timeout.

Vista opcional http://127.0.0.1:8765, lanzador PID32536: demo plan-3 con director/dados simulados, sin IA ni Firebase reales. No hay herramienta de pestaña IDE. Es secundaria y no debe retrasar desarrollo. El proceso cargó código anterior a cambios nuevos; reiniciar solo si hace falta mostrar su versión actual y tras comprobar identidad.

Git requiere escalación técnica de escritura .git/red. Push autorizado y despliegue por AGENTS.md: `git -c http.sslBackend=openssl -c http.sslCAInfo=.deps/windows-ca.pem push origin feature/rule-pack-engine`; main solo tras pruebas y avance compatible. No solicitar de nuevo aprobación rutinaria.

Historial completo anterior, con estados superados: HISTORIAL_REANUDAR_2026-11-06.md y HISTORIAL_REANUDAR_2026-11-05.md. No tratar sus sesiones «en curso» o versiones antiguas como estado actual. TRABAJO.md conserva evidencia cronológica; prevalece este punto y el estado comprobado de Git/producción.
