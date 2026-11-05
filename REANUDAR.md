# Reanudar el desarrollo

Bloque actual: director genérico conectado a estado/paquete, solicitud ligada a ficha, dados deterministas y continuación, interfaz y diario recuperable integrados. **360 pruebas completas con emulador correctas**, más 57 afectadas tras previsión de dados/retirada de solicitud desactualizada; navegadores de aventura, paquete y creador correctos con proveedor simulado. Siguiente inmediato: desplegar este bloque, verificar revisión/salud y ejecutar una sola sesión `.deps/verify_rule_director_live.py --release <hash>` (máximo tres inferencias; nunca repetir una sesión existente). Conservar capturas privadas; leer el último apartado de TRABAJO.md antes de continuar. No anunciar aplicación terminada.

Estado vigente del 5 de noviembre: **producción y origin/main en `7215c0a`, salud y revisión HTTPS comprobadas**. Motor genérico experimental accesible por creación explícita de sala, fuera del selector público (solo Pathfinder parcial). Dos inferencias reales de reglas propias: fuente incompleta ambigua y fuente completa con candidato; defecto de formato recuperado desde captura sin una tercera inferencia. Paquete instalado, ficha, tres acciones/dados, agotamiento, duplicado, invitado, copia y navegador móvil comprobados en producción. 347 pruebas completas con emulador correctas. Leer el último apartado de TRABAJO.md. **Siguiente: director de aventura genérico conectado con acciones/estado reales, manteniendo agencia, reglas y bajo coste**. No repetir guiones de inferencia existentes; sus sesiones privadas se conservan en `.deps`. Ya no falta una vía para comprobar el proveedor real; la clave local ausente no bloquea el desarrollo.

Último bloque: creación de personajes definida por el paquete (`character-creation` y `creation.action`), formulario generado, decisiones/dados/efectos confirmados conjuntamente, traza inicial y recuperación sin RNG. Ejemplo propio; no es creación completa de Pathfinder/Cairn ni un creador de varias etapas. Suite completa de 342 pruebas con emulador correcta; 35 pruebas del núcleo afectado y navegadores de creación/paquetes correctos. Siguiente: conversión real acotada y recorrido jugable genérico; comprobar accesos y camino de despliegue existente sin detener trabajo independiente.

Actualización actual: recuperación duradera de preparaciones en desarrollo, con reserva por campaña/actor/solicitud antes de inferir y captura privada de respuesta antes de validarla. Confirmación conserva un marcador mínimo para impedir nuevas llamadas desde solicitudes simultáneas antiguas. Leer el último apartado de TRABAJO.md; conversión real y recorrido genérico completo siguen pendientes. El objetivo permanece activo.

**Desarrollo reanudado por el usuario el 4 de noviembre de 2026.** Este archivo conserva el punto de pausa como referencia histórica; el estado actual se registra en TRABAJO.md. Vuelve a aplicarse la autonomía permanente.

Actualización del 5 de noviembre: el objetivo automático volvió a `active` tras el límite anterior. Composición de paquetes integrada en campaña/interfaz; suite completa de 293 pruebas con emulador oficial correcta, sin omisiones (93,602 s), navegador de composición y regresiones JSON/texto correctos. Siguiente bloque: identidad estable de fuentes y conservación/preparación de varios bloques de manual, manteniendo compatibilidad. La prueba de conversión real continúa pendiente; no se ha desplegado el sistema genérico. Leer siempre el último apartado de TRABAJO.md para superar las referencias históricas siguientes.

Avance posterior: fuentes `fragment-v2` estables y compatibles con `request-v1`, almacén normalizado de varios bloques, informes privados consultables localmente e instalación/composición desde candidatos guardados. **313 pruebas completas con emulador oficial correctas, sin omisiones (107,509 s)** y navegadores correctos. Próximo trabajo: separar ese almacén del estado de juego para no arrastrarlo en cada lectura/escritura mecánica, conservando confirmación consistente, permisos y copias. Proveedor real y recorrido genérico completo aún pendientes; no anunciar soporte universal ni entrega final.

Último avance: almacén privado separado en recursos inmutables Firestore por campaña/hash, referencia pequeña en instantáneas, caché acotada y omisión de transferencias repetidas al navegador. Exportación completa, aislamiento e indisponibilidad sin perder juego comprobados. **324 pruebas completas con emulador, sin omisiones (88,035 s)** y navegadores correctos. Siguiente punto: recuperación tras fallo de persistencia posterior a inferencia sin repetir coste, después conversión real y recorrido jugable. No se ha desplegado el motor genérico ni la nueva exclusión de índice.

Avance posterior: texto breve y rutas individuales desplegados y comprobados (main `0bd4b6d`). Rama de trabajo actual: `feature/rule-pack-engine`, tras aclarar el usuario que quiere entregar manuales e incorporar juegos sin programar cada sistema. El adaptador experimental de Cairn queda conservado en su rama; no continuar acumulando adaptadores por juego como arquitectura final. Intérprete, instalación JSON, interfaz, preparación asistida de texto y selección local de páginas PDF integrados en experimental: 42 pruebas con emulador, navegador PDF/texto/JSON y 62 regresiones de servidores correctos. Manual real Pathfinder p.87 abierto/extraído/renderizado localmente, sin IA ni envíos; original visual comprobado. Proveedor de conversión simulado; pendientes conversión real y procesamiento completo de manuales. Push de esta rama autorizado explícitamente; último respaldo previo `e56c8a2`. Mantener respaldos posteriores sin anunciar el prototipo como producto terminado. Al retomar, leer TRABAJO.md y PAQUETES_REGLAS.md antes de aplicar los pasos históricos de este archivo; no volver a integrar la antigua rama de pausa ni repetir inferencias reales.

## Punto guardado

- Proyecto: `C:\Users\Jonta\OneDrive\Proyectos\DM`.
- Rama de respaldo: `checkpoint/pausa-2026-11-04`. Se respalda en GitHub, sin desplegar esta rama.
- Producción y `origin/main`: **7e54a49**, en `https://dm-cronicas.onrender.com/`.
- Contrato del director comprobado: `generated-links-v4` en `/api/status`; `/api/status` también informa el commit desplegado.
- No hay servicios nuevos contratados ni un agente de desarrollo en la nube configurado. Cerrar VS Code interrumpe esta sesión local; Render y Firebase siguen funcionando por separado.

## Lo terminado y comprobado

1. Codificación: reparación local de secuencias dañadas en prosa del modelo y presentación de narraciones antiguas, sin alterar entradas del jugador ni originales exportados. Se comprobó en el historial real.
2. Agencia: contrato que distingue las declaraciones originales del jugador; una corrección real retiró un acercamiento no declarado del resumen. Sigue siendo una mitigación, no una garantía semántica absoluta.
3. Inicio y memoria de aventuras, preparación privada, objetivos y continuación tras resultados reales del motor.
4. Investigaciones de una escena: Percepción, elegir 10/20, pistas, requisitos y objetivo resueltos por código. Originales revisados: Reglas PDF p.87 (folio 86) y p.101. No hay combate ni temporizadores en este bloque.
5. Biblioteca de accesos y personajes por perfil del navegador, recuperación mediante archivo privado, apertura del original y copia inicial recalculada de nivel 1 sin transferir progreso.
6. Prueba real final **correcta**: IA genera ficción y dos búsquedas; el código crea ids y dependencias; dos investigaciones con elegir 20 localizan las pistas y completan el objetivo; una segunda narración real cierra la situación y guarda memoria en revisión 2. La ficha permanece intacta. No equivale a una campaña larga ni a cobertura completa de Pathfinder.

La comprobación estructurada acumuló seis intentos de inferencia: cuatro aperturas rechazadas durante la depuración y dos intervenciones exitosas de la versión corregida. No repetirlas automáticamente. No se midió su precio ni el consumo exacto de tokens. La campaña de prueba se conserva identificada como verificación; no se modificaron partidas personales anteriores.

## Trabajo guardado en la rama de pausa, aún sin desplegar

- `rulesets.py`: identidad explícita de sistema; solo Pathfinder 1e registrado como disponible, con cobertura parcial declarada.
- Normalización compatible de campañas antiguas y rechazo de importaciones que intenten usar sistemas no implementados. La identificación al leer no escribe en Firebase.
- `/api/systems`: catálogo local sin consultas a Firebase.
- `rules_sources/cairn-1e.json`: investigación de Cairn 1e, fuentes oficiales, licencia y hashes. **No es un sistema jugable ni seleccionable**. Solo se consultaron las secciones registradas; no presentar todo el SRD como auditado.
- Pruebas del registro y la compatibilidad. Última ejecución afectada: **64 pruebas correctas**, incluidos HTTP y Waitress. No se ha ejecutado la suite completa sobre esta última rama.

Última suite completa anterior: **166 pruebas con emulador oficial de Firestore, sin omisiones**. Después, la corrección de generación determinista pasó **76 pruebas afectadas** y la prueba real descrita. Playwright pasó aventuras, investigaciones, creador, tiradas y biblioteca (dos campañas, otro perfil, heridas originales, copia inicial, reanudación, protección de envíos pendientes y móvil).

## Informes y materiales locales que no deben publicarse

- `.deps/structured-live-report.json`: informe acumulado y resultado real final correcto.
- `.deps/structured-live-session.json`: credencial de la campaña de prueba y acciones confirmadas. **Privado; nunca mostrar el token ni subirlo a Git**. La prueba terminó, no queda un envío de esta campaña por recuperar.
- `.deps/adventure-live-session.json` y `.deps/adventure-live-report.json`: prueba anterior de apertura y diálogo.
- `.deps/agency-live-report.json`: corrección de agencia sobre esa campaña anterior.
- `.deps/rules-sources/`: originales oficiales descargados de Cairn, sin descarga o indexación por acción de juego.
- `.deps/reference-perception101.png` y `.deps/reference-take10-87.png`: comprobaciones visuales del manual original.
- Manuales del usuario en `C:\Users\Jonta\Desktop`; índices en `data/`. No subir manuales privados al repositorio.

El emulador de Firestore usado en `127.0.0.1:8181` se detuvo al pausar. No se dejan pruebas o verificaciones facturables ejecutándose.

## Primeros pasos al reanudar

1. Leer AGENTS.md, PRODUCTO.md, este archivo y TRABAJO.md. Comprobar rama y `git status`; revisar el remoto antes de integrar cambios. No descartar trabajo de la rama de pausa ni forzar un push.
2. Ejecutar la suite completa con el emulador sobre la rama de pausa. Solo ampliar las pruebas si aparece un fallo o se modifica algo relevante.
3. Integrar y desplegar el registro de sistemas cuando esté verificado; comprobar por HTTPS revisión y salud. Las credenciales Git funcionan fuera del aislamiento; los comandos anteriores usaron `git -c http.sslBackend=openssl -c http.sslCAInfo=.deps/windows-ca.pem ...`.
4. Continuar con aventuras aportadas en texto/documentos y varias escenas con rutas alternativas. Después, desarrollar un segundo adaptador real a partir de fuentes oficiales, preservando las reglas propias de cada sistema y los avisos de licencia. No anunciar Cairn como disponible antes de completar un bloque jugable y probado.
5. Ampliar presentación audiovisual coherente con el estado y recursos reutilizables, sin gastar IA por navegación o cálculo.

Para pruebas locales usar `.venv\Scripts\python.exe`. Sin emulador, las pruebas específicas de Firestore se omiten: no informar entonces «sin omisiones». El emulador está disponible en `.deps/firebase-emulators/cloud-firestore-emulator-v1.21.0.jar` y Java en `.deps/java21/jdk-21.0.12.1+1-jre/bin/java.exe`. Se inició con `--host 127.0.0.1 --port 8181 --project_id demo-cronicas-tests --rules firestore.rules --single_project_mode true`; las pruebas usan `FIRESTORE_EMULATOR_HOST=127.0.0.1:8181` y `FIREBASE_PROJECT_ID=demo-cronicas-tests`.

Frase suficiente para continuar: **«Reanuda el desarrollo desde REANUDAR.md»**.
