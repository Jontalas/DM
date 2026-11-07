# Reanudar el desarrollo

Estado vigente: **7 de noviembre de 2026**. Desarrollo activo por instrucción expresa del usuario: continuar análisis, código, pruebas, documentación y despliegue sin detenerse tras una entrega. Pedir intervención únicamente ante una dependencia imprescindible y continuar lo independiente. No hay bloqueo actual ni prueba personal que solicitar. No crear un goal inferido.

## Directiva permanente de sencillez

Aplicación extremadamente fácil de usar, pantallas claras sin saturación y guía contextual cuando sea necesaria. Mostrar primero situación y decisiones pertinentes; ayudas y herramientas secundarias bajo demanda, también con teclado y tacto. Requisito incorporado a AGENTS.md, PRODUCTO.md y USABILIDAD.md. Abrir ayudas/navegar no llama a IA ni escribe en Firebase. Aplicar también al revisar funciones existentes.

## Producción y respaldo

- Rama: feature/rule-pack-engine.
- Main/producción: **bf9389e677f09909737dedb9535e51b813debe52**, Render **7613620635 success**. Revisión exacta en /api/status y /healthz HTTPS200 verificadas. https://dm-cronicas.onrender.com.
- El aviso de armadura publicado coincide exactamente con el blob Git. Diferencia inicial frente al archivo local era CRLF, no un despliegue incorrecto.
- Producción incluye bienvenida simplificada, ayudas locales, dados bajo demanda y guía de mesa. El patio del peaje1.1.0: creador, PNJ de catálogo, acuerdo/combate por decisión propia, ataques/turnos automáticos, auxilio, estabilización, recuperación del único PJ hasta consciencia o muerte sin curar ni administrar horas, copia y recarga.
- Recuperación automática acotada a armaduras ligeras. Con cota de escamas conserva heridas/estabilidad y registra armor-rest, sin saltar descanso/fatiga. Aviso previo y motivo claros. Es límite del motor, no prohibición de Pathfinder. Definiciones1.0.0 y1.1.0 intactas; solicitudes antiguas sin encounterVersion conservan1.0.
- Última suite desplegada: **597 pruebas sin omisiones (214,397s)**, .deps/pf-recovery-armor-boundary-final-tests.log. Navegadores de recuperación, muerte, cota de escamas, copias y móvil correctos. Cero inferencias reales nuevas; ninguna partida personal modificada.
- Feature/origin posterior: **05e53e6**, aún no en main. Añade combatSerial/care-3 para no mezclar combates con las mismas fichas/orden, conserva care-1/2, planificador puro de eventos simultáneos y pf_rest.py (cálculo aislado de noche). **605 pruebas correctas sin omisiones (218,023s)**, .deps/pf-care-epoch-rest-final-tests.log;82 afectadas y navegador correctos. No es todavía controlador de recuperación de varios caídos ni descanso expuesto.

## Trabajo local actual: conservar y cerrar

Corrección de continuidad médica en engine.py/pf_recovery.py y pruebas. Una corrección positiva de PG negativos o una edición de notas no debe hacer perder consciencia ni borrar el dado original. recovery-state-2 conserva prueba/asistencia históricas y cadena de correcciones explícitas; no certifica ayuda actual tras una edición manual. Daño nuevo o alcanzar0 retiran el episodio negativo. Anotaciones posteriores de condiciones no invalidan una prueba pasada, pero bloquean nuevas resoluciones fuera del perfil. Cambiar Constitución con recuperación negativa no cubierta devuelve error claro sin modificar ficha.

94 pruebas afectadas correctas, incluidas dos HTTP/Waitress de corrección positiva, duplicado, condiciones y copia. Navegador TEST_PF_RECOVERY_CASE=correction correcto: corrección explícita, notas avanzadas, consciencia/dado original y copia por interfaz/recarga/móvil. Creador, pruebas de ficha, recuperación ligera y cota de escamas correctos después del cambio.

**Cierre verificado:**611 pruebas completas correctas sin omisiones (225,071s), .deps/pf-manual-health-continuity-final-tests.log. Sesión69362 terminada; tampoco quedan navegadores en curso. Desde el inicio de la suite solo se ajustó redacción del error de Constitución, sin cambios mecánicos. Respaldar y desplegar esta corrección verificada, comprobar Render y continuar con lo pendiente.

## Siguientes pasos

1. Suite69362 ya cerrada. Revisar diff y conservar corrección médica; respaldar feature y avanzar main con código probado. Verificar Render/revisión/salud. No repetir inferencias reales para cambios deterministas.
2. Continuar controlador de tiempo de varios pacientes: care-3 conserva época, ronda y cuenta; no inventar cuenta/época de datos antiguos ni mezclar combates. Los simultáneos deben resolverse juntos, sin omitir al PNJ cuando termina la espera del PJ.
3. Coordinar descanso natural8h, fatiga/armadura, consciencia y asistencia antes de aplicar pf_rest.py. El cálculo aislado no es una acción de descanso ni completa recursos/condiciones. No hay prioridad general de efectos coincidentes verificada atribuible al manual; no afirmar una ni saltar el evento.
4. Avanzar el recorrido del módulo: consecuencias, exploración/diálogo integrados, siguiente escena y reanudación. No convertirlo en sucesión indefinida de infraestructuras o ejemplos genéricos. adventure.validate_start actualmente impide mezclar pfEncounter e investigación tranquila; no quitar la barrera sin contrato, estado/tiempo compartido y pruebas.
5. Seguir revisión de claridad de USABILIDAD.md: entrada, ficha y diario, orientación pertinente y administración avanzada bajo demanda. No ocultar riesgos necesarios para decidir.

Los cuatro hitos personales de PRODUCTO.md siguen pendientes. No invitar por contadores de pruebas, despliegues o funciones parciales. Una invitación opcional futura tampoco detiene el desarrollo.

## Fuentes y límites

Reglas básicas Devir originales: PDF179/folio178, asalto6s y duración hasta misma cuenta;600 asaltos/hora. PDF190–192/folios189–191, incapacidad, estabilización, recuperación/curación. PDF151/150 y tabla6-6 PDF152/151, armaduras/sueño. Curar PDF93 encabeza Int pero tabla4-3 PDF90/listas/Sabiduría dicen Sab: se conserva el total Sab del creador y se documenta discrepancia, sin atribuir errata oficial.

La regla explícita de curación hasta0 o más de PDF191 fundamenta recobrar consciencia a0; no inventar una excepción por frase general «positivo» de PDF192. Negativos sin ayuda no curan naturalmente sin su prueba diaria, todavía pendiente. No inventar orden de descanso/prueba simultáneos. Consulta complementaria a FAQ oficial1e devolvió403; resultados2e descartados, no evidencia normativa.

NPC catálogo y licencias en CATALOGO_PNJ.md. RECUPERACION_PATHFINDER.md/ENCUENTROS_PATHFINDER.md describen evidencia y alcance. Fuentes/imágenes quedan privadas en .deps; no incluir manuales ni diagnósticos/tokens/exportaciones en Git.

## Método y entorno

Reutilizar Render/Firebase/Anthropic, sin nuevos servicios ni gastos recurrentes. Mecánicas deterministas; no IA por cálculo/ayuda/administración. Agrupar consecuencias y minimizar operaciones. No tocar partidas personales; no repetir guiones privados de producción existentes ni ensayos narrativos fallidos. Simulación y proveedor real se distinguen.

Pruebas por impacto; suite completa al cerrar motor y navegadores pertinentes. Skills ya usadas: debug, regression-testing, root-cause-analysis, interface-design. No subagentes sin petición explícita aplicable.

PowerShell, .venv/Scripts/python.exe; Playwright en .deps/browser-tests y Chrome instalado. Emulador127.0.0.1:8181, FIRESTORE_EMULATOR_HOST=127.0.0.1:8181, FIREBASE_PROJECT_ID=demo-cronicas-tests. Java conocido42040; comprobar identidad antes de terminar procesos. No reiniciar por timeout.

Vista opcional http://127.0.0.1:8765, lanzador conocido32536: demo plan-3 con datos/director/dados simulados, sin IA/Firebase reales; cargó código anterior. No hay herramienta de pestaña IDE. Es secundaria: no retrasar desarrollo ni pedir configuración para verla.

Escritura .git/red requiere escalación técnica de herramientas. Push y despliegue ya autorizados: git -c http.sslBackend=openssl -c http.sslCAInfo=.deps/windows-ca.pem push origin feature/rule-pack-engine; main tras pruebas/avance compatible. No pedir aprobación rutinaria otra vez.

Historial íntegro anterior en HISTORIAL_REANUDAR_2026-11-07.md, HISTORIAL_REANUDAR_2026-11-06.md y HISTORIAL_REANUDAR_2026-11-05.md. Sus «pendientes»/sesiones/versiones son históricos. TRABAJO.md conserva evidencia cronológica. Prevalecen este punto y Git/producción comprobados.
