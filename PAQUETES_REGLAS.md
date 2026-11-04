# Motor común y paquetes de reglas importables

## Objetivo y estado real

El usuario entrega reglas a la aplicación, que prepara e instala un paquete sin programar un adaptador por juego. El núcleo de partida interpreta esos datos; la IA ayuda a extraer fuentes y a dirigir ficción, no sustituye los cálculos. La incorporación de reglas debe llegar a ser un recorrido de la aplicación, con ambigüedades y límites visibles.

Estado actual: existe un primer intérprete local en `rule_pack_runtime.py`. No hay aún importador de manuales, instalador integrado ni creador/interfaz genéricos. Los adaptadores existentes siguen funcionando y conservan las campañas. Este núcleo es un paso hacia la arquitectura acordada, no una declaración de soporte universal ni la entrega final del recorrido «subir manual y jugar».

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

`RulePack` lee y valida el documento. `new_sheet(owner)` crea una ficha inicial; `view(sheet)` calcula su vista; `execute(sheet, action, inputs, actor, ...)` devuelve una ficha nueva y la trazabilidad. El núcleo es independiente del almacenamiento: no confirma en Firebase por sí mismo. La siguiente integración debe envolverlo con las versiones, permisos y marcadores de acción transaccionales existentes, conservando tiradas ante reenvíos.

La ficha queda ligada a identificador, versión y SHA-256 del paquete. No se reinterpreta silenciosamente con otro contenido, aunque conserve el mismo nombre o número de versión. Los cambios de versión necesitarán una migración explícita y probada.

Las acciones comprueban identidad, entradas y requisitos antes del RNG. Se validan también todos los valores físicos suministrados antes de tirar; se registra su origen. Los efectos se calculan desde la misma instantánea para evitar que el orden de asignación cambie una regla. Los desencadenantes se ejecutan por identificador ordenado hasta estabilizarse. Los objetos JSON no tienen orden semántico; las listas de tiradas y efectos sí forman parte del documento versionado.

No se modifica la ficha original. Errores, intervalos sin resultado, cálculos inválidos o ciclos de desencadenantes abortan toda la resolución. Los límites actuales incluyen 256.000 bytes por paquete, 128 campos, 128 acciones, 64 tablas, 64 desencadenantes, profundidad 20 de expresiones, presupuesto de ejecución y hasta 1.000 dados potenciales por acción. Se usan enteros acotados; no hay redondeos decimales implícitos. Las consultas a tablas usan índices de intervalos, sin recorrer todas sus filas en cada cálculo.

## Evidencia del primer bloque

Los archivos de prueba son documentos reales cargados por el mismo intérprete, sin registrar sus nombres en código:

- `test_fixtures/rule_packs/cairn-saves.json`: 3d6 y salvación d20 con 1 éxito/20 fallo. Basado en el SRD oficial 1e ya contrastado; atribución y CC BY-SA 4.0 conservadas. No implementa todo Cairn.
- `test_fixtures/rule_packs/pathfinder-skill-check.json`: habilidad preparada, d20 más total contra CD. Se volvió a revisar visualmente el original PDF p.87, folio 86 (`.deps/reference-take10-87.png`, privado). No hay texto del manual ni se afirma licencia para redistribuirlo. No calcula el creador ni el resto de Pathfinder.
- `test_fixtures/rule_packs/original-pool-example.json`: ejemplo propio de 2d6, recurso y agotamiento por desencadenante. No se presenta como otro juego comercial.

Diez casos automatizados comprueban 440 combinaciones de salvación y 300 de habilidad, diferencia de resultados naturales, versiones, conservación de entradas, permisos, lectura sin tiradas, tablas, dados conservados, tiradas condicionales, asignaciones simultáneas, límites y aborto ante ciclos/huecos. No equivalen a verificar todos los reglamentos ni a una sesión real con IA.

## Trabajo necesario para cumplir el objetivo

1. Integrar carga, inspección e instalación de paquetes en servidor e interfaz comunes, con aislamiento por campaña y sin nuevos despliegues por juego.
2. Generar formularios, ficha y acciones desde el paquete, con controles locales y validación autoritativa del servidor; ampliar creación guiada, colecciones/inventario, efectos y solicitudes de tirada mediante capacidades generales.
3. Añadir preparación asistida desde texto/PDF/documentos: extracción reutilizable, fragmentos y tablas pertinentes, propuesta de paquete, comparación con originales y pruebas. No repetir extracción ni inferencia por acción de partida.
4. Detectar operaciones no expresables, ambigüedades, ediciones incompatibles y permisos de uso. Resolver lo que pueda verificarse; solicitar una decisión solo cuando sea imprescindible. Ampliar primitivas comunes cuando falten, sin volver a adaptadores por juego.
5. Migrar por bloques las reglas verificadas existentes al formato y probar el recorrido completo, conservando campañas, datos privados y límites reales.

No activar automáticamente un paquete por superar el análisis sintáctico: compilar, pasar ejemplos y corresponder a las fuentes son comprobaciones distintas. Tampoco ejecutar código generado arbitrario como atajo a la importación sin programación.
