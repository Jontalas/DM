# Resoluciones y relato: causa raíz y contrato de trabajo

Estado del 5 de noviembre de 2026. Es análisis y planificación; no certifica funcionalidades pendientes ni un hito de prueba personal. Método aplicado: skill root-cause-analysis, revisión de capturas, cinco porqués y prevención comprobable. Responsable del siguiente trabajo: agente de desarrollo, dentro de las autorizaciones existentes, sin intervención imprescindible del usuario.

## Evidencia que se conserva

El primer ensayo integrado de fuente/PNJ/lugares/objetivos confirmó las mecánicas, pero añadió un acercamiento no declarado y volvió a pedir declarar una acción ya declarada. Sigue marcado sin aceptación narrativa. Otro ensayo, con creador por etapas y declaración natural, consumió exactamente tres llamadas: inicio capturado por ids tipados y recuperado sin inferencia adicional; solicitud Explorar correcta pero sin vínculo al objetivo; resolución correcta y continuación ambigua. El objetivo permaneció abierto como exigía el registro. La continuación mantuvo la marca poco legible pese al éxito confirmado e insinuó resolución del objetivo. No se retocan esos relatos ni se usan otras llamadas para sustituir evidencia desfavorable.

Las dos sesiones son técnicas, privadas y separadas de partidas personales. Fuentes propias CC0; no representan una aventura completa de Pathfinder. La suite y el navegador acreditan cálculo, persistencia, permisos y recorridos acotados; no prueban por sí solos comprensión semántica ni dirección satisfactoria de una campaña.

## Cinco porqués y factores

| Síntoma | Cadena causal comprobada | Corrección y límite |
|---|---|---|
| Ids tipados rechazados | El proveedor usó la notación de los extremos de relaciones en los ids de registros; el esquema dejaba esos ids como strings; la distinción se confiaba a prosa; los fixtures iniciales usaban siempre ids simples. | Enum de ids simples y extremos; recuperación exacta solo del inicio completo con procedencia/hash, sin inventar datos. Captura original recuperada sin otra llamada. No se generaliza una conversión arbitraria. |
| Objetivo no vinculado | La declaración natural produjo una acción legal, pero objectiveCheck era opcional; ausencia significaba no vincular; el motor hizo bien en no inferir intención ni cerrar después; los casos simulados positivos aportaban siempre el vínculo. | Evaluación explícita requerida cuando el esquema la admite; vacío explícito si no corresponde; aviso previo a resolver sin vínculo. Nuevas respuestas aún requieren comprobación real de pertinencia; un campo obligatorio no certifica interpretación. |
| Relato contradictorio después del éxito | El motor guardó valores correctos; se pidió al modelo interpretar un booleano y un historial con hipótesis anteriores; los hechos canónicos y la prosa no estaban separados en un contrato de presentación; validación estructural permitía una frase incompatible; las pruebas de aceptación técnica no podían sustituir la revisión del relato. | Debe reforzarse el paquete de hechos confirmados y su presentación determinista, conservando la ficción como complemento sin autoridad de estado. Más instrucciones de prompt o más patrones de texto no bastan para certificar coherencia. |

No se atribuyen estos defectos a la red, los dados ni Firestore: las trazas y las revisiones muestran que funcionaron. Tampoco se concluye que el proveedor sea incapaz en todos los contextos a partir de dos escenas. Se registra lo observado y se evita pagar reintentos para buscar una respuesta favorable.

## Siguiente contrato verificable

1. Declarar como datos qué campos del resultado de una acción son sus salidas relevantes, con fuentes y límites. El motor los obtiene tras efectos/desencadenantes incluso si un valor coincide con el anterior. Conservar formato y trazas antiguos cuando esa capacidad no exista.
2. Mostrar un resumen canónico de resultados calculado por código: acción, intención original, salidas relevantes y efectos/cierres de objetivo realmente registrados. Ninguna frase del proveedor debe convertirse por sí sola en cierre, recurso, desplazamiento o resultado mecánico.
3. Preparar para el director un paquete de resolución pequeño y explícito, con valores/etiquetas confirmados y objetivos cerrados o no cerrados. Evitar que deba reinterpretar fórmulas completas o priorice hipótesis anteriores sobre resultados posteriores.
4. Versionar la ampliación mediante una capacidad de paquete/contrato optativa para no cambiar huellas de solicitudes ya capturadas de campañas antiguas. Cualquier mejora de contexto debe conservar recuperación sin inferencia repetida; no introducir una migración implícita de intentos pendientes.
5. Añadir, cuando pueda trazarse a la aventura, consecuencias ficticias estructuradas ligadas a una solicitud/objeto y resultado concretos. No asignar a toda acción de un mismo tipo un objetivo o consecuencia de otra situación. No inventar fórmulas ni introducir efectos que la fuente/paquete no cubran.
6. Probar casos adversos: valor true ya existente que se recalcula, acción ajena a un objetivo, vínculo vacío, fracaso, éxito con un objetivo aún abierto, copia/reanudación, información privada y respuesta capturada bajo el contrato anterior. Separar siempre verdad calculada de evaluación de prosa.

Avance local posterior al análisis: puntos 1–4 implementados como capacidad optativa `action-results`, `resultFields`, traza `results`, presentación canónica y contexto `rule-pack-director-facts-2`. Los valores se toman después de efectos/desencadenantes y no dependen de que hayan cambiado. El contexto de continuación omite fórmulas e historial narrativo anteriores, conserva la declaración y los estados de objetivos, y distingue priorSummary de los hechos confirmados. No altera cálculos ni cierra objetivos sin vínculo. Las campañas sin la capacidad conservan contrato y huellas anteriores; un motor antiguo rechaza la capacidad nueva antes de invocar IA. Sigue siendo una capacidad general, sin adaptador por juego. Puntos 5–6, consecuencias ficticias estructuradas y aceptación semántica, no quedan resueltos por esta presentación; se mantienen pruebas adversas y revisión explícita.

Validación local: 424 pruebas completas con emulador correctas, sin omisiones (93,740 s); después 45 afectadas correctas (0,132 s) al precisar el rechazo de trazas malformadas. Navegadores de resultado repetido y aventura con objetivos/contexto nuevo correctos. Comparación local de bytes del mismo estado: contexto completo 3.754, proyección de hechos 2.701, reducción 1.053 bytes (28,1 %); sin inferencias para medir y sin afirmar ahorro real de tokens/precio. Despliegue y validación real de la nueva proyección pendientes en este punto.

No modificar manuales ni reproducir tablas no autorizadas. Antes de trasladar una mecánica de Pathfinder u otro juego, contrastarla con sus originales y registrar edición/páginas/permisos.

## Seguimiento y aceptación

Actualización de producción: action-results/facts-2 desplegados en ce6bf4254ca431b266b21851d4a0b620606380f9, con resultados repetidos, copia y navegador real verificados sin IA. Ensayo posterior de apertura simulada: una llamada (5.400 entrada/313 salida, sin thinking) propuso acción/vínculo correctos, pero describió una tirada pendiente en limitation; rechazo atómico correcto, respuesta conservada. No se ha probado todavía una continuación real facts-2. No se elimina esa limitación del original ni se repite la llamada. El prompt distingue ahora falta de cobertura de resolución pendiente; regresión comprueba rechazo sin dados ni cambios y equivalente legal con limitation vacía. Esta aclaración no certifica que futuras respuestas sean coherentes.

Por sesión técnica: máximo de llamadas fijado antes de comenzar, llamadas realmente efectuadas, uso observado, captura reutilizada, resultado del motor, persistencia/copia, privacidad, agencia y coherencia narrativa evaluados por separado. Registrar aceptación negativa sin alterar originales. El contador de pruebas no sustituye estas condiciones.

El hito de primera aventura autónoma completa de PRODUCTO.md permanece pendiente. El desarrollo continúa mientras se corrigen estos puntos y el motor/recorrido restante, sin pedir al usuario que pruebe cada entrega, configure fichas o desbloquee análisis que puede realizar el agente.
