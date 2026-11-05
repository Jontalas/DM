# Motor común y paquetes de reglas importables

## Objetivo y estado real

El usuario entrega reglas a la aplicación, que prepara e instala un paquete sin programar un adaptador por juego. El núcleo de partida interpreta esos datos; la IA ayuda a extraer fuentes y a dirigir ficción, no sustituye los cálculos. La incorporación de reglas debe llegar a ser un recorrido de la aplicación, con ambigüedades y límites visibles.

Estado actual: existe un primer intérprete local en `rule_pack_runtime.py`, su integración transaccional en `rule_pack_campaign.py`, interfaz genérica, preparación asistida y lectura local de páginas PDF. La integración permanece experimental, fuera del catálogo público; los recorridos de navegador habilitan el sistema únicamente en su servidor de pruebas. La conversión se ha comprobado con respuestas simuladas, no con inferencia real. No hay aún conversión de manuales completos. Los adaptadores existentes siguen funcionando y conservan las campañas. Este núcleo es un paso hacia la arquitectura acordada, no una declaración de soporte universal ni la entrega final del recorrido «subir manual y jugar».

## Contrato de datos v1

Un archivo JSON UTF-8 con `format: cronicas-rules-1` identifica juego, edición, versión, versión del motor, licencia/atribución, fuentes, cobertura implementada y pendiente, y capacidades requeridas. Cada campo, acción, tabla y desencadenante enlaza fuentes identificadas. Esas referencias son trazabilidad declarada: el analizador no certifica por sí solo que una interpretación corresponda al libro.

El motor reconoce capacidades, no nombres de juegos. Los identificadores del paquete son opacos. Los datos no pueden importar módulos Python, acceder a archivos/red, invocar IA ni evaluar instrucciones de los documentos como código.

| Definición | Función actual |
|---|---|
| `fields` | Enteros, booleanos y texto con límites/opciones; valores iniciales o fórmulas derivadas |
| Expresiones | Referencias, suma, resta, producto, división con suelo, mínimo/máximo, comparaciones, condiciones y concatenación |
| `tables` | Intervalos numéricos con resultado escalar; sin solapamientos y sin inventar resultados para huecos |
| `actions` | Entradas tipadas, requisitos, tiradas y efectos simultáneos |
| `rolls` | Cantidad/tamaño configurables, conservar todos o los mayores/menores y tiradas condicionales |
| `triggers` | Efectos automáticos sobre el estado hasta estabilizarse, sin bucles abiertos |

Una referencia, por ejemplo `{"ref":["fields","dex"]}`, lee un campo definido. `{"op":"le","args":[{"ref":["rolls","save","total"]},{"ref":["fields","dex"]}]}` expresa comparar una tirada con ese valor. El significado reglamentario se define en el paquete y se revisa contra su fuente; el núcleo solo proporciona operaciones.

Los valores calculados no se guardan como copias editables: se derivan al consultar. Las tiradas solo se producen al ejecutar acciones. Navegar, consultar o calcular una ficha cargada no usa RNG, IA ni base de datos.

## Resolución y persistencia

`RulePack` lee y valida el documento. `new_sheet(owner)` crea una ficha inicial; `view(sheet)` calcula su vista; `execute(sheet, action, inputs, actor, ...)` devuelve una ficha nueva y la trazabilidad. El núcleo es independiente del almacenamiento: no confirma en Firebase por sí mismo. `rule_pack_campaign.py` lo integra con las versiones, permisos y marcadores de acción transaccionales existentes, conservando tiradas ante reenvíos. Un único adaptador genérico atiende paquetes con identificadores nuevos sin registrar cada juego en Python.

El anfitrión instala el paquete en borrador. Para ejecutar sus definiciones debe seleccionar expresamente la política de reglas aportadas (`provided-rules`): esto no certifica correspondencia con el manual. No se admite declarar una política «verificada» desde el cliente. Las fichas se crean con valores iniciales, no mediante un creador completo. La sustitución del paquete se bloquea cuando existen fichas hasta disponer de migraciones verificadas. En esta versión los campos y el paquete son compartidos por los miembros autorizados de la campaña; no hay campos privados ni soporte de secretos dentro del paquete.

La inspección estructural es local y sin almacenamiento, IA ni dados. La caché de compilación se acota y separa por campaña. La recuperación reproduce las resoluciones con los dados guardados y compara trazas y estado final; no vuelve a tirar ni certifica la identidad histórica de un archivo externo. Al importar una copia, la propiedad se reasigna al anfitrión. El estado se limita a 750.000 bytes y el importador a 5.000 entradas, sin borrar automáticamente historial.

La ficha queda ligada a identificador, versión y SHA-256 del paquete. No se reinterpreta silenciosamente con otro contenido, aunque conserve el mismo nombre o número de versión. Los cambios de versión necesitarán una migración explícita y probada.

Las acciones comprueban identidad, entradas y requisitos antes del RNG. Se validan también todos los valores físicos suministrados antes de tirar; se registra su origen. Los efectos se calculan desde la misma instantánea para evitar que el orden de asignación cambie una regla. Los desencadenantes se ejecutan por identificador ordenado hasta estabilizarse. Los objetos JSON no tienen orden semántico; las listas de tiradas y efectos sí forman parte del documento versionado.

No se modifica la ficha original. Errores, intervalos sin resultado, cálculos inválidos o ciclos de desencadenantes abortan toda la resolución. Los límites actuales incluyen 256.000 bytes por paquete, 128 campos, 128 acciones, 64 tablas, 64 desencadenantes, profundidad 20 de expresiones, presupuesto de ejecución y hasta 1.000 dados potenciales por acción. Se usan enteros acotados; no hay redondeos decimales implícitos. Las consultas a tablas usan índices de intervalos, sin recorrer todas sus filas en cada cálculo.

## Evidencia del primer bloque

Los archivos de prueba son documentos reales cargados por el mismo intérprete, sin registrar sus nombres en código:

- `test_fixtures/rule_packs/cairn-saves.json`: 3d6 y salvación d20 con 1 éxito/20 fallo. Basado en el SRD oficial 1e ya contrastado; atribución y CC BY-SA 4.0 conservadas. No implementa todo Cairn.
- `test_fixtures/rule_packs/pathfinder-skill-check.json`: habilidad preparada, d20 más total contra CD. Se volvió a revisar visualmente el original PDF p.87, folio 86 (`.deps/reference-take10-87.png`, privado). No hay texto del manual ni se afirma licencia para redistribuirlo. No calcula el creador ni el resto de Pathfinder.
- `test_fixtures/rule_packs/original-pool-example.json`: ejemplo propio de 2d6, recurso y agotamiento por desencadenante. No se presenta como otro juego comercial.

Diez casos automatizados comprueban 440 combinaciones de salvación y 300 de habilidad, diferencia de resultados naturales, versiones, conservación de entradas, permisos, lectura sin tiradas, tablas, dados conservados, tiradas condicionales, asignaciones simultáneas, límites y aborto ante ciclos/huecos. No equivalen a verificar todos los reglamentos ni a una sesión real con IA.

La primera integración añade siete casos repetidos bajo HTTP y Waitress: inspección sin almacenamiento, instalación reservada al anfitrión, borrador y política explícita, identificador nuevo sin código específico, deduplicación de dados, recurso y desencadenante atómicos, propiedad, rechazo previo al RNG, recuperación sin azar, rechazo de valores/trazas/hash alterados y límite de historial sin pérdida de eventos. Resultado conjunto: 24 pruebas correctas con el emulador oficial de Firestore (10,468 s). Regresión del registro, HTTP existente y Waitress: 62 pruebas correctas (35,863 s).

`test_rule_pack_browser.cjs` comprueba selección del sistema experimental al crear sala, archivo inválido sin escritura, revisión, borrador y activación explícita, ficha desde definiciones, acciones y entradas numéricas con valores predeterminados, dados físicos, fallo reglamentario sin cambio, agotamiento automático, respuesta perdida y recuperación con el mismo identificador, recarga, exportación/importación con reasignación y permisos de invitado. Carga dos documentos diferentes sin añadir código por juego. Editar entradas y consultar fichas no envía acciones ni repite la inspección. La biblioteca local guarda solo identidad de fichas propias, sin inventar clases/niveles ni copiar reglas o campos. Móvil revisado visualmente, sin desbordamiento horizontal. Pasan también los recorridos existentes de biblioteca, creador PF, tablero y Cairn experimental, y la prueba local de biblioteca ampliada. Navegador usa almacén desechable, no Firebase remoto ni IA. No se ha desplegado este bloque.

## Trabajo necesario para cumplir el objetivo

### Composición determinista e integración

`rule_pack_composition.py` combina paquetes completos del mismo juego, edición y atribución con una versión posterior. Fusiona fuentes idénticas por identificador y referencias adicionales para definiciones iguales; rechaza conflictos sin elegir por orden ni sobrescribir. No elimina cobertura pendiente por inferir que otro bloque la haya resuelto. Recompila el resultado y conserva las huellas de entrada en una procedencia separada. El núcleo no instala ni migra estado.

La interfaz permite añadir paquetes a una campaña todavía sin fichas, revisar la combinación sin guardar y elegir borrador o uso explícito. El guardado común vuelve a componer, verifica las huellas base/resultado y conserva la procedencia. Los permisos, versiones y marcadores transaccionales impiden instalaciones ajenas/obsoletas y duplicación tras respuesta perdida. Activar el mismo borrador no elimina su procedencia. La copia importada comprueba formato y enlace de la procedencia, pero no autentica por sí sola las entradas históricas de un archivo externo.

Veintinueve pruebas de composición e integración HTTP/Waitress correctas con emulador (33,815 s), más Playwright de conflictos, revisión sin escritura, recuperación, activación, ambas acciones y móvil. Solo reglas propias de ejemplo. Faltan generación/acumulación de bloques parciales desde fuentes y composición con referencias externas sin resolver; este recorrido no equivale a importar un manual completo por capítulos.

Suite completa de la rama tras integrar composición y transferencia local por bloques: **293 pruebas correctas con emulador oficial, sin omisiones (93,602 s)**. No se han ejecutado inferencias reales ni desplegado esta integración.

### Preparación asistida de fragmentos: primer recorrido

El anfitrión aporta título, edición, atribución, ámbito de uso declarado, alcance y texto. El servidor admite hasta 32 páginas/fragmentos con numeración única y 24.000 caracteres de texto en total; la interfaz permite un fragmento `.txt`/`.md` UTF-8 o varias páginas seleccionadas de un PDF local. No se envía el resto de la campaña al proveedor. El ámbito de uso es una declaración del aportante, no una comprobación jurídica ni una licencia concedida por la aplicación.

La preparación tiene huella SHA-256 del contenido y metadatos; cada fragmento tiene hash propio y referencia asignada por la aplicación. Una llamada a Haiku, con hasta 8.000 tokens de salida, propone datos o declara ambigüedades/operaciones no expresables. No se ejecutan instrucciones de los documentos como código. El motor rechaza referencias, identidad o atribución alteradas, operaciones desconocidas y ejemplos con resultados incorrectos o dados ausentes; no genera azar para completarlos. Superar esos controles solo demuestra consistencia estructural e interna, no correspondencia semántica con el manual.

Las nuevas referencias usan `fragment-v2`, estable para el mismo documento/edición/página/texto y PDF original, aunque cambien el alcance o la versión del paquete. La huella de la solicitud sigue siendo independiente. Preparaciones y capturas antiguas sin `sourceScheme` conservan `request-v1`, sin renombrar ni reinterpretar sus reglas. Esto permite que dos bloques nuevos reutilicen una referencia de la misma página al componerlos; no demuestra equivalencia automática de referencias heredadas de otro esquema. Sesenta pruebas afectadas con emulador correctas (30,442 s), incluidos importación y replay heredados sin IA; navegador de texto y PDF correcto.

La preparación se guarda separada del paquete activo y solo el anfitrión recibe su texto original e informe. Los invitados siguen viendo las definiciones compartidas del paquete instalado, no los fragmentos privados. El almacén normalizado conserva varios bloques; reenviar la misma acción confirmada o intentar preparar el mismo contenido ya guardado, aunque no sea el último, no repite inferencia. Revisar un informe, recargar, instalar, importar una copia y ejecutar reglas no llama al preparador. Los errores no tienen reintentos automáticos, aunque una inferencia fallida puede haber consumido tokens; no se promete ejecución exactamente una vez del proveedor ante una caída anterior a la confirmación persistida.

### Almacén privado de bloques preparados

`rule_preparation_workspace.py` conserva metadatos/informes por hash de solicitud, fuentes por identificador y textos por hash de contenido. Las páginas de cada bloque refieren al catálogo compartido; no se repite el párrafo original en cada solicitud guardada. Incluso referencias v1/v2 distintas pueden compartir los mismos bytes de texto sin renombrar sus fuentes ni declarar equivalencia de reglas. Se admiten hasta 128 bloques/4.096 referencias dentro de un límite privado de 750.000 bytes, independiente de los 750.000 bytes de estado de juego del motor experimental; el máximo de elementos no garantiza que quepan todos. Se comprueba capacidad antes de inferir, sin eliminar automáticamente informes o fuentes.

Las preparaciones antiguas siguen leyéndose desde `authoring`; al confirmar una escritura se pueden normalizar y separar físicamente sin renombrar sus fuentes. Una inferencia o importación fallida conserva el estado anterior. La copia administrativa comprueba referencias, hashes, metadatos, ejemplos y ausencia de fuentes/textos huérfanos. El invitado no recibe `authoringWorkspace` ni su referencia privada. No se envía una segunda copia expandida del almacén: el navegador reconstruye cada informe localmente a partir de sus referencias. La consulta del archivo no escribe ni llama a IA; instalar un candidato anterior o añadirlo al paquete mediante la composición sí requiere una acción explícita validada por servidor.

Evidencia: suite completa **313 pruebas correctas con emulador oficial, sin omisiones (107,509 s)**. Playwright pasa dos bloques de una página con un solo texto, conservación tras recarga, informes distintos consultados sin acciones, instalación del anterior, composición del candidato guardado, efecto automático, invitado y móvil. Siguen pasando composición por archivo, texto, PDF y paquetes JSON. Propuestas simuladas, sin inferencias reales ni despliegue.

### Recurso privado separado del estado de juego

`rule_workspace_asset.py` y el almacén Firestore separan el contenido normalizado en `campaigns/<cid>/ruleWorkspaces/<sha256>` (bajo el prefijo configurado). Se conserva comprimido, con hash del JSON canónico, validación de integridad y descompresión acotada. La instantánea de juego guarda una referencia pequeña `authoringWorkspaceRef`. El recurso se prepara antes de publicar la instantánea; versión y marcador de acción siguen confirmándose en el mismo batch atómico. Un fallo previo no cambia la campaña ni confirma el marcador, aunque puede dejar datos preparados sin referencia, como ocurre con las instantáneas existentes.

Las acciones mecánicas no cargan ni vuelven a guardar el recurso privado. El anfitrión lo recibe al cargarlo por primera vez o cuando cambia su hash. Los siguientes refrescos incluyen el hash conocido y reciben `workspaceUnchanged`, sin retransmitir el contenido; el navegador conserva únicamente la copia del mismo acceso/campaña. Una respuesta atrasada de otro acceso no reemplaza la campaña actual. La caché del servidor mantiene hasta ocho recursos confirmados en bytes, separada por campaña, con carga fría agrupada por bloqueo y sin objetos mutables compartidos. El invitado no solicita ni recibe el recurso.

La exportación siempre expande las fuentes y retira la referencia interna; no acepta una copia importada que intente apuntar a recursos privados del servidor. Si las fuentes están ausentes o dañadas, la interfaz informa de esa condición, conserva el juego y permite las mecánicas del paquete instalado. La copia completa falla expresamente, sin entregar un archivo que finja incluir originales perdidos. La lectura privada tiene un intento acotado y se puede reintentar expresamente; no produce llamadas al modelo.

Coste por recorrido comprobado: un recurso nuevo se escribe una vez antes de confirmar la nueva referencia; una primera lectura fría autorizada obtiene un documento, las siguientes usan caché por hash. Una acción mecánica usa el recorrido normal de instantánea/marcador y cero lecturas/escrituras adicionales de fuentes privadas. El paquete de reglas activo y el resto del estado todavía viajan en las instantáneas; no se declara optimización universal. La exclusión de índice para `ruleWorkspaces.data` queda preparada en `firestore.indexes.json`, no desplegada aún. No se añade servicio.

Retención: no se borran automáticamente recursos privados ni versiones anteriores; el limpiador existente solo procesa `snapshots`. Antes de limpiar recursos sin referencia habrá que comprobar la instantánea vigente y todas las instantáneas retenidas/copias necesarias. Los recursos preparados por una confirmación fallida pueden quedar huérfanos; se conservan para evitar eliminar material recuperable hasta disponer de una auditoría de referencias. No activar borrado por edad únicamente.

Evidencia tras separación: **324 pruebas completas con emulador oficial correctas, sin omisiones (88,035 s)**. Incluyen integridad/descompresión, recuperación fría, caché sin mutación ni cruce de campañas, ausencia de operaciones privadas en acciones/reenvíos mecánicos, fallo de preparación sin confirmar y fuentes no disponibles sin perder juego ni producir copia incompleta. Playwright comprueba omisión real del cuerpo privado en refrescos/acciones, archivo local, exportación completa, recarga y carrera al cambiar de acceso. Archivo por bloques, biblioteca, creador PF y tablero siguen pasando. Proveedor simulado; sin inferencias reales ni despliegue.

Solo un candidato sin cuestiones bloqueantes puede pasar a revisión e instalación explícitas; `ambiguous`/`unsupported` se conservan como informe no ejecutable. La instalación queda ligada al hash de la preparación para rechazar revisiones obsoletas. Con fichas existentes se bloquea preparar sustituciones hasta disponer de migraciones. Al importar una copia administrativa se comprueban de nuevo hashes y ejemplos, sin IA ni RNG. El original y el informe permanecen privados dentro de esa copia.

Evidencia de este bloque: 37 pruebas de preparación, intérprete e integración HTTP/Waitress correctas con emulador oficial de Firestore (17,145 s). Playwright con proveedor simulado pasa texto local sin envíos al editar, propuesta única, informe conservado, instalación separada, acción del paquete, aislamiento del invitado, mecánica no disponible y móvil; captura revisada visualmente. El recorrido JSON anterior y biblioteca existente siguen pasando. No se han realizado inferencias reales ni despliegue de este bloque.

### PDF local y origen de las páginas

`static/rule-source-pdf.js` usa PDF.js 6.5.438 con worker, cargado únicamente al seleccionar un PDF válido. Se distribuye desde la propia aplicación, sin CDN ni servicios añadidos. `scripts/vendor_pdfjs.py` verifica la integridad SHA-512 publicada por npm antes de copiar los archivos originales y sus licencias; el manifiesto conserva SHA-256 y tamaño de cada recurso. No se incluye el visor ni el sandbox de scripting/QuickJS. Los 201 recursos suman 4.648.128 bytes; módulo y worker iniciales suman 1.746.199 bytes y el resto se consulta cuando el documento lo necesita. Las rutas fijadas por versión permiten caché inmutable; navegar por páginas no consulta IA ni Firebase.

Referencias de implementación: [documentación y ejemplos oficiales](https://mozilla.github.io/pdf.js/examples/index.html), [API oficial](https://mozilla.github.io/pdf.js/api/draft/api.js.html), [release fijada](https://github.com/mozilla/pdf.js/releases/tag/v6.5.438). Licencias originales en `static/vendor/pdfjs-6.5.438/` y procedencia en su manifiesto. La nueva API se cierra mediante la tarea de carga, no mediante `PDFDocumentProxy.destroy`.

Límites: PDF de hasta 128 MiB y 2.500 páginas; cada preparación selecciona hasta 32 páginas y 24.000 caracteres. El lector conserva solo el documento consultado y hasta 64 extracciones de página en memoria. Se muestran páginas originales con un máximo aproximado de dos millones de píxeles. La selección mantiene numeración PDF, hash del archivo y versión del extractor; cambiar la selección invalida el texto anterior hasta aplicarla. Los campos extraídos son de consulta, sin mezclar silenciosamente texto editado con el origen PDF. Volver a texto aportado retira el origen PDF de esa preparación.

El PDF binario permanece local y no se guarda en Firebase. En la preparación privada se conservan los textos elegidos y el origen declarado por el cliente; el servidor no recibe el binario y no certifica por sí mismo ese hash ni la autenticidad del manual. Al recargar, el anfitrión puede volver a seleccionar el archivo y el lector compara su hash antes de mostrarlo como original coincidente. No se borra ni modifica el archivo. No hay OCR; páginas sin texto extraíble y documentos que requieren contraseña indican la limitación. La extracción conserva el orden del contenido, pero no certifica columnas/tablas: se ofrece el original para cotejarlo. La IA sigue recibiendo texto, no imágenes de las páginas.

Evidencia PDF: 42 pruebas de intérprete, preparación, procedencia, recursos e integración HTTP/Waitress con emulador oficial correctas (20,057 s), más 62 regresiones de servidores correctas (48,299 s). Playwright comprueba carga diferida, render real, elección y exclusión de páginas, ausencia de envíos por navegación, vuelta a texto sin origen obsoleto, página sin texto, caché de extracción, hash coincidente/distinto tras recarga y móvil; proveedor de propuesta simulado. Se corrigieron una carrera entre carga/selección y el cierre incompatible con la API nueva. Un fallo aislado de transporte local al leer un recurso pasó en la comprobación específica y en la siguiente suite completa del bloque; no se modificó la prueba para ocultarlo.

También se abrió el manual privado real de Pathfinder (93.828.277 bytes): PDF p.87, 6.388 caracteres extraídos y cero acciones enviadas. Original renderizado completo contrastado visualmente con la referencia previa, folio 86. Captura privada en `.deps/rule-source-original-p87.png`; no se publica el manual ni su texto. Esto prueba lectura/render de esa página, no conversión automática de todo Pathfinder ni fidelidad de una propuesta de IA.

1. Carga, inspección e instalación JSON integradas y probadas en servidor e interfaz comunes; pendiente habilitar el recorrido tras completar las dependencias de producto. No requiere un registro nuevo por identificador de paquete.
2. Formularios, ficha inicial y acciones escalares generados desde el paquete con validación del servidor; pendientes creación guiada completa, colecciones/inventario, efectos amplios y solicitudes de tirada mediante capacidades generales.
3. Preparación asistida de texto y páginas PDF integrada y probada con proveedor simulado. Pendientes procesamiento de manuales por bloques reutilizables, OCR/documentos adicionales, revisión estructurada de tablas y validación con proveedor real. No repetir extracción ni inferencia por acción de partida.
4. Detectar operaciones no expresables, ambigüedades, ediciones incompatibles y permisos de uso. Resolver lo que pueda verificarse; solicitar una decisión solo cuando sea imprescindible. Ampliar primitivas comunes cuando falten, sin volver a adaptadores por juego.
5. Migrar por bloques las reglas verificadas existentes al formato y probar el recorrido completo, conservando campañas, datos privados y límites reales.

No activar automáticamente un paquete por superar el análisis sintáctico: compilar, pasar ejemplos y corresponder a las fuentes son comprobaciones distintas. Tampoco ejecutar código generado arbitrario como atajo a la importación sin programación.
