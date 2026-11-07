# Reanudar el desarrollo

Estado vigente: **7 de noviembre de2026**. Desarrollo activo. Continuar análisis, código, pruebas, documentación y despliegue sin detenerse tras una entrega. Pedir intervención solo ante dependencia imprescindible; seguir lo independiente. No hay bloqueo actual ni prueba personal que solicitar. No crear goal inferido ni subagentes sin petición aplicable.

## Directivas permanentes

Aplicación extremadamente sencilla, información clara sin saturar y guía contextual accesible. Situación y decisiones primero; detalles y administración bajo demanda. Ayudas/navegación no llaman IA ni escriben Firebase. Requisitos en AGENTS.md, PRODUCTO.md y USABILIDAD.md.

Objetivo: aventuras persistentes sin maestro humano; IA para ficción/intenciones, motor determinista para reglas/estado y agencia del jugador. Roll20 como referencia funcional, manuales originales de Pathfinder/Bestiario/TREY para módulo actual. Otros sistemas mediante paquetes de datos, sin prometer cobertura universal. Reutilizar Render/Firebase/Anthropic, mínimo coste y sin servicios recurrentes nuevos.

## Producción y verificación

- Rama feature/rule-pack-engine.
- Feature/main/producción: **677aa38cc23a0deb64cb4e06c7deb050a232dc26**. Render **7615003439 success**, revisión exacta en /api/status release, /healthz HTTPS200 y descriptor1.3.0 comprobados. https://dm-cronicas.onrender.com.
- Suite final **635 pruebas completas correctas sin omisiones (259,956s)**, .deps/pf-scene-continuity-guard-final-tests.log, sesión50419 terminada. Primera suite632 (291,689s) precedía guardas posteriores. Ninguna suite en curso.
- Navegadores correctos: creador/encuentro, recuperación compartida, continuidad por acuerdo/combate, investigaciones/rutas anteriores, copias/recarga/móvil. Detalles en CONTINUIDAD_PATHFINDER.md/RECUPERACION_PATHFINDER.md.
- Producción anterior98b1452 (Render7614727297) incluía recuperación1.2 con624 pruebas;0cdc5ba anterior tenía continuidad médica611. Son históricos.

## Recorrido1.3 publicado

Creador legal; patio preparado con NPC catálogo; decisión propia de acuerdo/combate; iniciativa, ataques, auxilio, estabilización y recuperación acotada automáticos. Definiciones1.0/1.1/1.2 intactas; solicitudes sin encounterVersion conservan1.0. Nuevas entradas seleccionan descriptor1.3.

Reloj1.2/1.3 comparte cuentas reales de ambos caídos y resuelve simultáneos completos. Recibo2 reproduce paciente/dado al importar. Sin curación ni decisiones del PJ. Armadura ligera, asistencia conocida care-3 misma época; ambos negativos solo primer combate corto. PNJ asistido todavía inconsciente detiene reloj6h antes de descanso curativo pendiente. Límite conservador del motor, no regla. Armadura scale mantiene armor-rest sin avanzar horas. Legacy1.1 PJ asistido no entra en bucle de recuperación sin ayuda.

Continuidad1.3: continue_pf_encounter instala escena original El recibo del patio en misma localización. Conserva personajes, tablero, heridas, tiempo y encuentro; no viaja, cura ni llama IA. Requiere PJ positivo y PNJ no negativo o muerto, sin condiciones/perfil alterado/eventos pendientes. Cada búsqueda/resolución pendiente revalida: lesión posterior bloquea antes de RNG. Recibo pfContinuation liga hashes y módulo; importación rechaza huérfanos/pistas sustituidas. UI ofrece una decisión; al continuar retira tarjeta anterior y muestra investigación. No quitar barrera genérica adventure.validate_start para mezclar aventuras arbitrarias.

## Ensayo real ya terminado: NO REPETIR

.deps/pf-continuity-live-session.json está **verified**. Campaña técnica separada: creador/acuerdo, transición, diálogo real, dos búsquedas, continuación real, duplicados y copia/importación. Dos solicitudes de director, latencias cliente12.995ms y8.459ms; fichas16/7PG conservadas, sin pendientes ni pistas anticipadas. Ninguna campaña personal modificada. Tokens/precio no expuestos; no inventar estimación.

Primer error TypeError del guion ocurrió antes de IA por argumento kind duplicado. Se corrigió helper y --resume-before-provider verificó cero solicitudes previas/versión exacta para continuar misma campaña. **Ahora tampoco se puede repetir ese modo**, pues ya se consumió el ensayo. No borrar/renombrar sesión para generar otra. Guion .deps/verify_pf_continuity_live.py debe negarse a repetir. Nunca imprimir ni publicar tokens/exportación/diagnósticos.

Navegador real .deps/verify_pf_continuity_browser.cjs correcto: campaña reanudada, móvil sin desbordamiento, cero POST de acciones e inferencias por consulta. Captura privada pf-continuation-production-mobile.png revisada.

## Trabajo local actual y paso inmediato

Ajuste narrativo ya publicado677aa38: pauta de estilo natural, sin cambiar reglas/contexto/esquema ni reescribir textos.13 afectadas correctas (8,138s), incluida recuperación de la misma captura con otra huella de prompt sin proveedor. No repetir ensayo real por estilo.

**Diario local verificado, aún sin commit:** static/index.html/static/app.js y test_journal_browser.cjs. Resumen legible de lugar/objetivo/notas; personas e incógnitas bajo demanda. Formulario/cambio manual de escena en detalles solo anfitrión. Se ocultan secciones vacías; pendientes reales visibles. Datos escapados y secretos fuera del resumen. Navegador nuevo correcto: teclado sin escrituras, una corrección explícita, HTML literal, invitado sin edición/secretos, recarga/móvil. Captura journal-guided-mobile.png revisada. Mesa de dos jugadores, módulos y continuidad1.3 por acuerdo/combate correctos. Prueba AssetTests correcta; no suites/navegadores en curso. Motor sin cambios: no repetir suite635.

1. Revisar y respaldar/publicar diario probado. Verificar Render/revisión/salud sin IA ni campañas personales.
2. Seguir recorrido y sencillez: revisión de ficha, decisiones pertinentes y orientación. No parar tras publicación.
3. Continuidad pendiente: consecuencias/hallazgos hacia siguiente localización y campaña, sin perder participantes ni relojes. Investigación actual registra acciones pero no calendario exacto; nunca usarla para omitir recuperación.
4. Descanso completo pendiente: noche8h, fatiga/armadura, asistencia y curación diaria sin ayuda. pf_rest.py es cálculo aislado, no acción. No hay prioridad general verificada de efectos coincidentes; no inventarla ni saltarla.
5. Los cuatro hitos personales de PRODUCTO.md siguen pendientes. Ensayo o despliegue parcial no invita a prueba personal. Invitación opcional futura tampoco detiene desarrollo.

## Fuentes y método

Originales comprobados: Reglas PDF179/178, asalto6s y misma cuenta;190–192/189–191, incapacidad/estabilización/recuperación;151/150 y152/151 armaduras/sueño. Percepción PDF101 y elegir10/20 PDF87 revisados visualmente de nuevo para continuidad. CD de investigación es adjudicación propia, no tabla oficial. Curar93 encabeza Int pero tabla90/listas/Sab dicen Sab; motor conserva Sab, discrepancia documentada. Bestiario goblin PDF167/166, fuente/edición/licencias en CATALOGO_PNJ.md.

No igualar inconsciencia y noche de sueño ni inventar amanecer. Curación hasta0 funcional según regla explícita PDF191. Fuente complementaria FAQ1e403 no cuenta como evidencia; resultados2e descartados.

No tocar partidas personales ni repetir ensayos pagados anteriores. Código determinista por cálculo, consecuencias agrupadas y mínima IA/Firestore. Privados/originales/capturas permanecen en .deps ignorado, nunca Git.

## Entorno

PowerShell, .venv/Scripts/python.exe; Playwright .deps/browser-tests y Chrome instalado. Emulador127.0.0.1:8181, FIRESTORE_EMULATOR_HOST=127.0.0.1:8181 y FIREBASE_PROJECT_ID=demo-cronicas-tests. Java conocido42040; comprobar identidad antes de terminar procesos. No reiniciar por timeout. Logs pueden envolver ResourceWarning como NativeCommandError: prevalece resultado final OK.

Vista opcional http://127.0.0.1:8765, lanzador32536: demo plan-3 con datos/director/dados simulados, código de servidor anterior. No herramienta de pestaña IDE; no retrasar desarrollo para esto.

Skills ya aplicadas: debug, regression-testing, root-cause-analysis, interface-design. .git/red requieren escalación técnica; push/despliegue ya autorizados:
git -c http.sslBackend=openssl -c http.sslCAInfo=.deps/windows-ca.pem push origin feature/rule-pack-engine
y push origin HEAD:main tras validación compatible. No pedir aprobación rutinaria.

Archivos JS locales CRLF pueden diferir de hash remoto LF; comparar blob Git o normalizar. Buscar con rg -g '*.js' static, no static/*.js en PowerShell. Leer UTF8. No insertar literales Unicode mediante tubería Python que los convierta en interrogantes.

Historial íntegro anterior en HISTORIAL_REANUDAR_2026-11-07_CONTINUIDAD.md y archivos11-07/11-06/11-05. Son históricos; prevalecen este punto, Git y producción comprobada. TRABAJO.md conserva evidencia cronológica.
