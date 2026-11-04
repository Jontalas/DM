# Motor común y paquetes de reglas importables

## Objetivo y estado real

El usuario entrega reglas a la aplicación, que prepara e instala un paquete sin programar un adaptador por juego. El núcleo de partida interpreta esos datos; la IA ayuda a extraer fuentes y a dirigir ficción, no sustituye los cálculos. La incorporación de reglas debe llegar a ser un recorrido de la aplicación, con ambigüedades y límites visibles.

Estado actual: existe un primer intérprete local en `rule_pack_runtime.py`, su integración transaccional en `rule_pack_campaign.py` y una interfaz genérica en `static/rule-pack-ui.js`. La integración permanece experimental, fuera del catálogo público; los recorridos de navegador habilitan el sistema únicamente en su servidor de pruebas. No hay aún importador de manuales. Los adaptadores existentes siguen funcionando y conservan las campañas. Este núcleo es un paso hacia la arquitectura acordada, no una declaración de soporte universal ni la entrega final del recorrido «subir manual y jugar».

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

1. Carga, inspección e instalación JSON integradas y probadas en servidor e interfaz comunes; pendiente habilitar el recorrido tras completar las dependencias de producto. No requiere un registro nuevo por identificador de paquete.
2. Formularios, ficha inicial y acciones escalares generados desde el paquete con validación del servidor; pendientes creación guiada completa, colecciones/inventario, efectos amplios y solicitudes de tirada mediante capacidades generales.
3. Añadir preparación asistida desde texto/PDF/documentos: extracción reutilizable, fragmentos y tablas pertinentes, propuesta de paquete, comparación con originales y pruebas. No repetir extracción ni inferencia por acción de partida.
4. Detectar operaciones no expresables, ambigüedades, ediciones incompatibles y permisos de uso. Resolver lo que pueda verificarse; solicitar una decisión solo cuando sea imprescindible. Ampliar primitivas comunes cuando falten, sin volver a adaptadores por juego.
5. Migrar por bloques las reglas verificadas existentes al formato y probar el recorrido completo, conservando campañas, datos privados y límites reales.

No activar automáticamente un paquete por superar el análisis sintáctico: compilar, pasar ejemplos y corresponder a las fuentes son comprobaciones distintas. Tampoco ejecutar código generado arbitrario como atajo a la importación sin programación.
