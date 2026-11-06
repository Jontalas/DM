# Reanudar el desarrollo

Estado actualizado el 5 de noviembre de 2026. Este documento contiene el estado vigente. El historial anterior completo se conserva, sin reinterpretarlo, en [HISTORIAL_REANUDAR_2026-11-05.md](HISTORIAL_REANUDAR_2026-11-05.md); sus instrucciones de despliegue, contadores y «pendientes» son históricos.

## Continuidad y prioridades

Continuar autónomamente desarrollo, pruebas, documentación y despliegue dentro de las autorizaciones existentes. Una entrega no termina el trabajo: avanzar al siguiente punto sin pedir «continúa». Intervención del usuario únicamente ante una dependencia imprescindible. No generar servicios ni gastos recurrentes nuevos. No enviar mensajes externos. Mantener la agencia de los jugadores y automatizar administración mediante código determinista, con mínimo uso de IA y Firebase.

AGENTS.md y PRODUCTO.md gobiernan el producto: aventuras persistentes sin maestro humano, mesa al estilo Roll20, motor reglamentario y varios sistemas modulares. Completar primero un recorrido del módulo actual. Pathfinder/TREY exige contraste previo con los tres originales y trazabilidad de edición/página; ejemplos propios CC0 del kernel no acreditan reglas Pathfinder ni un segundo sistema oficial.

Los cuatro grandes hitos de prueba personal de PRODUCTO.md siguen pendientes. No pedir pruebas personales por estos bloques técnicos. El usuario quiere vistazos ocasionales de la aplicación corriendo, preferiblemente en pestaña IDE, como apoyo secundario que no retrase trabajo.

## Repositorio y producción confirmados

- Rama de trabajo: feature/rule-pack-engine.
- Último bloque de código desplegado: **d4816bd83d802777701f82dd831ce87e4509d1ec** (main/origin y feature).
- Producción: https://dm-cronicas.onrender.com, Render **7588288003 success**, revisión exacta en /api/status y /healthz HTTPS 200 confirmados.
- Desplegados: perfiles de creación de PJ/PNJ, actores privados, plan-2 importable con PNJ preparados, selector explícito abstracto, resolución atómica de dos fichas, evidencia privada reproducible y proyección pública acotada.
- Incluye vínculos preparados de objetivos de aventura a PNJ concretos mediante plan-3. No incluye combate espacial/PF, turnos automáticos de PNJ ni interpretación dirigida por texto libre. El preparador automático excluye target-sheets/abstract-scene-targets hasta admitir ejemplos completos de dos fichas.

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

Resultado final del bloque plan-3: **506 pruebas completas con emulador correctas sin omisiones (213,075 s)**. Después, trece pruebas de rutas/recorrido incluyendo formas/orígenes inválidos correctas. Navegador plan-2 también correcto. Desplegado y verificado: `.deps/target-objective-live-session.json` verified con apertura simulada, cero inferencias, objetivo/revelación/dos fichas/copia/invitado correctos y continuación no invocada. No repetir el guion. Navegador de producción anfitrión/invitado/copia/móvil correcto, objetivo completado y descubrimiento visibles, cero acciones al consultar; captura `.deps/target-objective-production-mobile.png`.

Siguiente bloque **integrado localmente**, 6 de noviembre: RECUPERACION_CONCURRENTE.md. `pending_randomness.py` describe una reserva por solicitud/propietario, elecciones/fichas/mundo, independiente de id/versión HTTP cuando solo cambia OOC. Scope pending-resolution-v2 solo en solicitudes nuevas. ActionRandomness/Firestore/TestStore confirman esa clave en el mismo lote; servidor mantiene CAS y preflight. Si no genera dados, una lectura sin escritura comprueba que no esté sustituyendo una reserva existente por dados físicos; si genera dados, usa la reserva normal sin lectura adicional. Navegador recupera primero envío original y, ante 409 con la misma solicitud nueva, un único cuerpo con id/versión vigentes y mismas decisiones, persistido antes de enviar. Sin IA adicional.

Pruebas: descriptor/HMAC y Firestore/CAS/cliente nuevo correctos; HTTP/Waitress de fallo de commit + OOC de otro jugador + cuerpo antiguo rechazado + cambio a físicos rechazado + cliente nuevo preservan [5,6], fichas/objetivo/revelación y duplicado. Navegador de recuperación y regresión plan-3 correctos. Suite completa en curso: sesión **61059**, `.deps/pending-recovery-final-tests.log`. Completar antes de respaldo/despliegue. feature/origin tiene checkpoint e4d0a0d; cambios posteriores de integración están locales. Main/producción siguen 4439a0b. Todavía no afirmar recuperación concurrente desplegada.

Cierre local de recuperación concurrente: **518 pruebas completas con emulador correctas sin omisiones (221,200 s)**, `.deps/pending-recovery-final-tests.log`. Captura antigua original revalidada localmente sin IA; navegador de recuperación y plan-3 correctos. Respaldar/desplegar/verificar revisión exacta y salud antes de anunciar producción. No se han hecho más inferencias reales. Después priorizar recorrido reglamentario del módulo actual y automatización de PNJ desde fuentes originales, en vez de seguir ampliando indefinidamente ejemplos técnicos; PRODUCTO.md mantiene hito individual pendiente.

Despliegue de recuperación confirmado en la revisión indicada arriba. `.deps/pending-scope-live-session.json` verified, cero inferencias, apertura simulada, ámbito pending-resolution-v2, dados reales servidor [4,2], fallo mecánico conservado (objetivo abierto y sin revelación), duplicado/copia correctos y continuación no invocada. No repetir el guion. La inyección de fallo/OOC/cliente nuevo sigue acreditada por emulador, no se provocaron fallos en producción.

Siguiente análisis reglamentario ya iniciado: Bestiario original Devir PFR002, depósito B 5055-2014; PDF 3 incorpora erratas 2.0 equivalentes a tercera reimpresión inglesa. Entrada Goblin **PDF 167 / folio 166**, vista del original: combatiente 1, **PG 7 (1d10+2) con +1 de clase predilecta**, CA16/toque13/desprevenido14, espada corta +2 1d4/19–20, iniciativa+6, velocidad30 pies. No usar recuerdos ni sustituir por guerrero humano de PG máximos. Original/ilustración/ficción no se redistribuyen. PDF3 y licencia PDF328/folio327 revisados visualmente; mecánica declarada Open Content y licencia 1.0a/avisos deben acompañar cualquier incorporación pública de datos. Imágenes y extracto solo .deps/book-pages y .deps/bestiary-license-original.txt. Todavía no hay plantilla goblin implementada ni encuentro autónomo nuevo; contrastar capacidades, límites del combate y permisos antes de activar. Leer PRODUCTO.md y CREACION_PERSONAJES.md para priorizar primer recorrido actual, no anunciar hito por un perfil.

Actualización posterior: primer preparador **aislado** npc_catalog.py con catalogs/npc-catalog.json implementado. Sin API/encuentro habilitado. Cuatro pruebas específicas y veinticinco con creador/combate correctas, crítico real con espada corta Pequeña. Bestiario PDF7/folio6 confirma espacio/alcance estándar omitidos; Reglas básicas PDF143/folio142 y185/folio184 verificados visualmente para espada corta y×2. Licencias/avisos originales de ambas fuentes incluidos en licenses/ (Core PDF570/folio569 comprobado); solo datos reglamentarios identificados como Open Game Content, sin imágenes ni ficción. Arco/munición/visión/cambio de arma/tesoro/PX pendientes explícitos. CATALOGO_PNJ.md define siguiente incorporación atómica, procedencia/permisos/colocación y encuentro de aventura; no anunciar perfil aislado como aventura autónoma. Cambios de este bloque todavía locales hasta respaldar.

Estado local posterior, 6 de noviembre: fábrica respaldada en feature/origin **a9f199b**; main/producción conservan03c2b2b. Integrada localmente API `create_npc`, solo anfitrión, sin estadísticas directas, fuera de combate, hasta16, casilla libre; propiedad director y procedencia `npcCreation` por huella de plantilla (no del catálogo completo). Copia valida valores originales salvo PG dinámicos y conserva PNJ/director, reasignando solo PJ. Edición avanzada marca corrección excepcional y no convierte PNJ en PJ; consulta del invitado es solo lectura. Auditoría de fuentes omitida del contexto IA, estadísticas actuales conservadas.

Licencias servidas mediante lista exacta /licenses/ de tres archivos públicos, sin Firebase; copia de campaña con PNJ incluye textos/avisos una sola vez en campo raíz licenses, sin escribirlos en cada estado ni enviarlos a IA. Trece pruebas afectadas de exportación/HTTP/Waitress/licencias correctas y navegador de PNJ anfitrión/invitado/móvil correcto, cero acciones al consultar. Suite completa anterior al último ajuste legal: **530 correctas sin omisiones (222,759 s)**. Suite final actual en curso: sesión **80800**, `.deps/npc-preparation-final-legal-tests.log`. Terminar antes de commit/despliegue del API. No hay interfaz de creación ni encuentro autónomo nuevo: siguiente paso será preparación de encuentro y activación por decisión del jugador, más desenlace/reanudación; revisar originales para cualquier mecánica nueva, sin asumir muerte de PNJ a0PG ni teletransporte de PJ.

Cierre final del API de PNJ: **531 pruebas completas con emulador correctas sin omisiones (230,223 s)**; `.deps/npc-preparation-final-legal-tests.log`. Navegador correcto tras enlaces directos a avisos originales, fuente/propiedad director, nombre escapado y corrección manual marcada; invitado sin guardar. Respaldar/desplegar/verificar revisión/salud y una preparación técnica aislada sin IA, incluidos avisos/exportación/copia. Fuente de plantilla versionada no debe cambiar silenciosamente; futuras versiones deben conservar recuperación de entradas anteriores. No se ha ejecutado otra inferencia narrativa.

API de PNJ desplegada/verificada en revisión d4816bd indicada arriba. `.deps/npc-catalog-live-session.json` verified, cero inferencias y ninguna aventura iniciada: PG7/CA16/ataque+2/1d4, director, duplicado, invitado sin preparar, copia conserva PNJ/reasigna PJ, textos de licencia incluidos y públicos correctos. Navegador producción anfitrión/invitado/copia/móvil correcto, cero acciones/IA por consultar; `.deps/npc-catalog-production-mobile.png`. No repetir guion. No equivale a encuentro autónomo ni a aceptación narrativa.

Próximo bloque de fiabilidad necesario para el encuentro real: el módulo PF heredado todavía usa engine.dice/secrets directamente y su desempate de iniciativa usa randbits, mientras las semillas duraderas anteriores cubrían rule-pack. Conectar una fuente de dados por contexto de ejecución (aislada entre hilos) a ActionRandomness y al commit existente, incluyendo desempates, sin cambiar fórmulas o probabilidades ni reservar datos para acciones sin dados/físicos. Primero pruebas de fallo de commit y cliente nuevo del combate PF/NPC, antes de automatizar su encuentro. Recuperación entre versiones intermedias sigue limitada a solicitudes rule-pack con scope2; no extender esa promesa al combate PF sin contrato específico.

Actualización local posterior: game_randomness.py conectado al servidor/engine PF, ContextVar por ejecución y desempates de16bits dentro de la reserva. Pruebas de hilos/contextos y HTTP/Waitress: fallo de commit/cliente nuevo mantienen iniciativa/desempate, dados rápidos y ataque/daño/PG/acción gastada. Físicos y preparación NPC no consultan/reservan semillas. Navegadores creador/ataque y PNJ correctos con doble simulado. **543 pruebas completas con emulador correctas sin omisiones (236,338s)**, .deps/pf-durable-dice-final-tests.log. DADOS_PERSISTENTES.md detalla alcance/coste. Respaldar/desplegar/verificar antes de afirmar producción. Preparado .deps/verify_pf_durable_dice_production.py: copia una preparación técnica ya verificada en una sala nueva, tira dados/iniciativa/ataque normales y comprueba duplicado/copia; cero IA y sin inyección de fallos en producción. Sesión pf-durable-dice-live-session.json aún no creada; no repetir guiones existentes.

Después: ampliar recorrido autónomo completo, recuperación/concurrencia con cambios intermedios de versión, reglas verificadas del módulo actual y capacidades de mesa en PRODUCTO.md. No asumir alcance, visibilidad individual o iniciativa por conocer un PNJ.

## Vista local secundaria

http://127.0.0.1:8765, `scripts/preview_local.py`. Datos desechables, perfiles propios, director simulado, sin Anthropic/Firebase. Muestra plan-3 con dos PNJ preparados, selector explícito y objetivo vinculado a Arda. Navegador comprobado, cero acciones al consultar; fuentes tipográficas normales sí usan Google Fonts. No existe herramienta disponible para controlar una pestaña del IDE; ya se informó sin pedir configuración al usuario.

Último lanzador conocido **50452**, tras verificar/terminar 51124. Comprobar HTTP antes de arrancar otra instancia. Para reiniciar, verificar primero con Get-CimInstance que el PID corresponde a scripts/preview_local.py y terminar solo ese árbol. Arrancar oculto mediante Start-Process, logs `.deps/local-preview.log` y `.deps/local-preview-error.log`. No detener otros procesos. Los cambios Python necesitan reiniciar este proceso; no hacerlo por cada edición si retrasa el trabajo.

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
