# Reanudar el desarrollo

Estado actualizado el 5 de noviembre de 2026. Este documento contiene el estado vigente. El historial anterior completo se conserva, sin reinterpretarlo, en [HISTORIAL_REANUDAR_2026-11-05.md](HISTORIAL_REANUDAR_2026-11-05.md); sus instrucciones de despliegue, contadores y «pendientes» son históricos.

## Continuidad y prioridades

Continuar autónomamente desarrollo, pruebas, documentación y despliegue dentro de las autorizaciones existentes. Una entrega no termina el trabajo: avanzar al siguiente punto sin pedir «continúa». Intervención del usuario únicamente ante una dependencia imprescindible. No generar servicios ni gastos recurrentes nuevos. No enviar mensajes externos. Mantener la agencia de los jugadores y automatizar administración mediante código determinista, con mínimo uso de IA y Firebase.

AGENTS.md y PRODUCTO.md gobiernan el producto: aventuras persistentes sin maestro humano, mesa al estilo Roll20, motor reglamentario y varios sistemas modulares. Completar primero un recorrido del módulo actual. Pathfinder/TREY exige contraste previo con los tres originales y trazabilidad de edición/página; ejemplos propios CC0 del kernel no acreditan reglas Pathfinder ni un segundo sistema oficial.

Los cuatro grandes hitos de prueba personal de PRODUCTO.md siguen pendientes. No pedir pruebas personales por estos bloques técnicos. El usuario quiere vistazos ocasionales de la aplicación corriendo, preferiblemente en pestaña IDE, como apoyo secundario que no retrase trabajo.

## Repositorio y producción confirmados

- Rama de trabajo: feature/rule-pack-engine.
- main/origin y feature respaldados en **3b43f4fd0c2428e4e330c40cca9b465d442ecd52**.
- Producción: https://dm-cronicas.onrender.com, Render **7587164446 success**, revisión exacta en /api/status y /healthz HTTPS 200 confirmados.
- Desplegados: perfiles de creación de PJ/PNJ, actores privados, plan-2 importable con PNJ preparados, selector explícito abstracto, resolución atómica de dos fichas, evidencia privada reproducible y proyección pública acotada.
- No incluye combate espacial/PF, turnos automáticos de PNJ, objetivos de aventura sobre PNJ concretos ni interpretación dirigida por texto libre. El preparador automático excluye target-sheets/abstract-scene-targets hasta admitir ejemplos completos de dos fichas.

Historial técnico de estas capacidades en PAQUETES_REGLAS.md, ACTORES_Y_OBJETIVOS.md, RESOLUCIONES_ENTRE_FICHAS.md y PREPARACION_AVENTURAS.md. No repetir despliegues ni verificaciones que ya constan terminados sin un cambio o fallo nuevo.

## Corrección local actual: continuación pública

Ensayo real nuevo `.deps/actor-plan-director-live-session.json`: **dos llamadas de dos**, 11.354 tokens entrada/868 salida. Inicio con plan-2, actores, prueba física [3,4], ambas fichas y recuperación correctos; **narrativeAcceptance=false**, fase verified-mechanics-with-narrative-issues. La continuación reveló la carta privada de Arda y confundió la prueba abstracta con investigar la marca. Conservar esta evidencia negativa. **No repetir el guion ni gastar más llamadas para obtener aceptación.**

Corrección posterior desplegada y verificada:

- Las nuevas resoluciones guardan `continuationScope:public` en su evidencia privada y usan `rule-pack-director-target-public-facts-7`.
- Solo entrega registros conocidos con private vacío y hechos verificados. Excluye fuente, preparación y resumen anterior; evita recuperar la fuente remota por esta continuación.
- Esa respuesta no puede actualizar registros. La preparación privada real se conserva para siguientes intervenciones.
- Las resoluciones antiguas sin marca conservan target-facts-5 y contexto anterior, para no invalidar capturas pagadas.
- Pruebas de no filtración/no lectura/no sobrescritura/compatibilidad y HTTP/Waitress correctas; navegador plan-2 correcto. Comparación del mismo resultado original: 4.189→3.718 bytes, carta ausente, cero llamadas al medir. No equivale a tokens facturados ni aceptación narrativa real del contrato 7.
- Suite completa terminada: **499 pruebas correctas sin omisiones (209,526 s)**, log `.deps/public-target-final-tests.log`. Después: seis pruebas específicas de rutas/límites y dos HTTP/Waitress de continuación sin leer fuente correctas; eliminada la importación incidental de tres pruebas duplicadas del selector en el nuevo módulo de pruebas. La suite previa plan-2: 489 correctas (210,018 s).

Ensayo mecánico de producción `.deps/public-target-live-session.json` verified, cero inferencias, apertura simulada, marca continuationScope:public confirmada, ambas fichas/duplicados/copia/invitado correctos. No repetir ese guion. No repetir inferencias reales en esta fase; la aceptación narrativa real del contrato 7 sigue sin verificar.

## Siguiente desarrollo ya iniciado

OBJETIVOS_DIRIGIDOS.md define el contrato pendiente. `objective_targets.py` compila y selecciona rutas por acción, PNJ y entradas normalizadas, exige resultado booleano propio incondicional, rechaza ambigüedad y limita también los valores predeterminados expandidos. **Seis pruebas específicas correctas**. `RulePack.action_inputs` extrae la misma normalización de entradas que ya usaba el runtime; 20 pruebas de runtime/creador/perfiles y 36 afectadas posteriores correctas.

Integración **local posterior** conectada: plan-3 añade objectiveTargets, prepara vínculo privado y su huella junto al catálogo, deriva objetivo/descubrimientos antes de dados y confirma ambas fichas/cierre/revelaciones juntos. Director usa contrato target-objectives-8 y no ofrece objetivos reservados a PNJ entre sus propuestas individuales. Recuperación comprueba huella/cronología y acción/PNJ/decisiones de la evidencia. Plan-1/2 mantienen recorrido anterior. Siete pruebas nuevas de recorrido correctas; dos HTTP/Waitress de fallo de commit/cliente Firestore nuevo verifican dados [5,6] preservados, dos fichas/objetivo/revelación y duplicado sin IA. Navegador plan-3 completo correcto con proveedor simulado. Suite completa en curso, sesión **25345**, log `.deps/target-objective-final-tests.log`. Terminar antes de respaldo/despliegue; no anunciar objetivos dirigidos disponibles en producción todavía. Ejemplo propio test_fixtures/original-target-objective-plan.json. Nada de esto añade reglas Pathfinder ni certificación narrativa.

Resultado final del bloque plan-3: **506 pruebas completas con emulador correctas sin omisiones (213,075 s)**. Después, trece pruebas de rutas/recorrido incluyendo formas/orígenes inválidos correctas. Navegador plan-2 también correcto. Preparado .deps/verify_target_objective_production.py, sesión target-objective-live-session.json aún no creada: usar solo tras verificar despliegue exacto; apertura simulada, cero inferencias, no continue. Próximo bloque de fiabilidad analizado en RECUPERACION_CONCURRENTE.md; todavía no implementado, no omitir CAS ni cambiar claves de semillas sin su barrera atómica.

Después: ampliar recorrido autónomo completo, recuperación/concurrencia con cambios intermedios de versión, reglas verificadas del módulo actual y capacidades de mesa en PRODUCTO.md. No asumir alcance, visibilidad individual o iniciativa por conocer un PNJ.

## Vista local secundaria

http://127.0.0.1:8765, `scripts/preview_local.py`. Datos desechables, perfiles propios, director simulado, sin Anthropic/Firebase. Muestra selector explícito abstracto y campos compartidos del PNJ. Navegador comprobado, cero acciones al consultar; fuentes tipográficas normales sí usan Google Fonts. No existe herramienta disponible para controlar una pestaña del IDE; ya se informó sin pedir configuración al usuario.

Último lanzador conocido **51124**. Comprobar HTTP antes de arrancar otra instancia. Para reiniciar, verificar primero con Get-CimInstance que el PID corresponde a scripts/preview_local.py y terminar solo ese árbol. Arrancar oculto mediante Start-Process, logs `.deps/local-preview.log` y `.deps/local-preview-error.log`. No detener otros procesos. Los cambios Python necesitan reiniciar este proceso; no hacerlo por cada edición si retrasa el trabajo.

## Verificación y herramientas

PowerShell en C:\Users\Jonta\OneDrive\Proyectos\DM. Python `.venv/Scripts/python.exe`. Emulador Firestore activo en 127.0.0.1:8181; suite:

```powershell
$env:FIRESTORE_EMULATOR_HOST='127.0.0.1:8181'
$env:FIREBASE_PROJECT_ID='demo-cronicas-tests'
.venv/Scripts/python.exe -m unittest discover -q
```

Guardar logs de suites largas en .deps para no perder el resultado entre sesiones. Playwright en `.deps/browser-tests/node_modules/playwright`, Chrome del sistema. Producción Node requiere NODE_EXTRA_CA_CERTS apuntando a `.deps/windows-ca.pem`; no desactivar TLS. Git push autorizado usando http.sslBackend=openssl y http.sslCAInfo=.deps/windows-ca.pem; comprobar cada resultado, sin force push. `.deps/inspect_dm_deployment.py` usa credenciales del helper y solo muestra metadatos; ejecutarlo sin imprimir credenciales. No hay rechazo de auto-review registrado.

Skills ya aplicadas: regression-testing, debug, root-cause-analysis e interface-design. No usar subagentes sin petición explícita aplicable. No hay goal activo creado; no inferir uno.

## Evidencias privadas y límites permanentes

`.deps` está ignorado y contiene tokens, copias, diagnósticos y capturas. Nunca publicar, imprimir ni enviar sesiones completas, exportaciones privadas o diagnósticos codificados. Originales y capturas negativas permanecen intactos. No rerun de scripts de creación/evaluación; cada uno reserva su sesión y se niega a repetirla.

- `abstract-target-live-session.json`: verificación mecánica real del bloque anterior, cero inferencias, apertura simulada, duplicados/copia/invitado correctos. Navegador producción anfitrión/invitado/copia/móvil correcto, cero acciones; `abstract-target-production-mobile.png`.
- `actors-live-session.json`, `adventure-plan-live-session.json`, `discoveries-live-session.json`: mecánicas verificadas sin IA y aperturas simuladas identificadas; no equivalen a aceptación narrativa.
- `rule-director-live-session.json`: captura original recuperada sin nueva inferencia; `.deps/replay_rule_director_live.py` reproduce localmente. No ejecutar guion de creación otra vez.
- `source-director-live-session.json`: tres llamadas, 17.445 entrada/1.642 salida; agencia/repetición defectuosas, aceptación falsa. Sin cuarta llamada.
- `staged-adventure-live-session.json`: tres llamadas, 16.256 entrada/1.560 salida; objetivo no vinculado y continuación defectuosa, aceptación falsa. Sin cuarta llamada.
- `facts-director-live-session.json`: una llamada fallida, 5.400 entrada/313 salida; propuesta contradice limitation. No consumir llamada restante para buscar un resultado favorable.
- `actor-plan-director-live-session.json`: dos llamadas agotadas y aceptación falsa, descrita arriba. No reescribirla como éxito tras la corrección.

Exclusiones de índices para adventureSources/ruleWorkspaces/preparationAttempts siguen siendo administración pendiente; desplegar código no las aplica. Mantener protección de datos, originales y copias. Toda función pendiente o excepcional debe identificarse como tal.
