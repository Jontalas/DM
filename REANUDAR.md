# Reanudar el desarrollo

Pausa solicitada por el usuario el **4 de noviembre de 2026**. No continuar ni programar trabajo hasta que el usuario pida reanudar. La instrucción de autonomía permanente vuelve a aplicarse cuando reanude.

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
