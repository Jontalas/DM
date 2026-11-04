# Investigaciones estructuradas: primer bloque ejecutable de aventuras

## Recorrido

En «Iniciar aventura con IA» se puede generar una investigación breve, elegir «La carta perdida» o importar un JSON compatible. La aventura se instala en la misma acción que guarda la apertura: no requiere preparar pistas o estadísticas manualmente. Una generación solicitada como estructurada no se acepta si falta el módulo validado.

La escena muestra las investigaciones disponibles para el personaje que controla cada jugador. Se puede buscar con d20, elegir 10 o elegir 20. Cada opción directa agrupa solicitud, resolución, hallazgo y progreso en una sola confirmación de estado, sin IA. Una declaración libre equivalente puede ser interpretada por el director mediante `investigation`; el servidor valida personaje, oportunidad y requisitos antes de solicitar la prueba. No utiliza una CD proporcionada por el cliente o inventada para esa intervención.

Antes de instalar se comprueba que las pistas obligatorias y sus requisitos sean alcanzables por los totales preparados del grupo dentro de este bloque. Si no lo son, se rechaza la instalación, sin alterar la CD del autor ni simular una solución. No es un equilibrador general de encuentros o aventuras.

Al tener éxito se revela la pista correspondiente y se habilitan las dependientes. El motor actualiza los objetivos y publica la conclusión cuando se cumplen sus requisitos. La narración posterior recibe esos resultados y no puede reabrir ni completar objetivos por su cuenta. Localizar un objeto no decide recogerlo, abrirlo o entregarlo.

## Cobertura y autoridad

Solo Pathfinder 1e: una localización tranquila, sin combate, amenazas, distracciones, límites de tiempo, penalizaciones por fallo, pruebas enfrentadas o modificadores situacionales pendientes. El personaje debe tener Percepción preparada y no presentar condiciones que requieran revisión. La CD es una adjudicación del autor de la aventura y se identifica como tal; no se atribuye una CD personalizada a una tabla del manual.

Se comprobaron visualmente los originales de Reglas básicas de Pathfinder 1e, Devir (identificación de edición en README): PDF p.87, folio impreso 86, pruebas y elegir 10/20; PDF p.101, Percepción, acción y reintento. La búsqueda deliberada es una acción de movimiento y el reintento es posible mientras persista el estímulo. Elegir 10 requiere ausencia de amenazas y distracciones; elegir 20 exige además tiempo suficiente y ausencia de penalización por fallo.

El alcance `single-scene-neutral-perception` declara esas condiciones de uso. El motor bloquea combate, condiciones del personaje y otras pruebas o excepciones pendientes. Se registra una acción de búsqueda o veinte al elegir 20. La duración exacta y los efectos dependientes del tiempo no se calculan: no usar este bloque para una cuenta atrás. No se consume una acción de combate fuera de combate ni se introduce una equivalencia de segundos inventada.

La conversación conserva decisiones libres y respuestas de PNJ. Las vías alternativas que excedan el grafo de investigaciones todavía pueden requerir adjudicación excepcional; no hay un simulador universal que valide cualquier plan. Una aventura de varias escenas, combate o conjuros no es compatible con este formato todavía. No se sustituye Pathfinder por una simplificación silenciosa.

## Formato e importación

El archivo usa `format: cronicas-adventure-1`, `ruleset: pathfinder-1e` y el alcance anterior. Incluye título, premisa, localización, descripción pública, objetivo, preparación privada, conclusión condicionada, oportunidades y objetivos. La referencia ejecutable está en adventure_modules.py y el ejemplo propio en adventures/la-carta-perdida.json.

Cada oportunidad tiene id, etiqueta pública, CD, texto de hallazgo, texto de fallo y requisitos de pistas previas. Cada objetivo identifica las pistas necesarias. El servidor rechaza claves desconocidas, efectos mecánicos no soportados, duplicados, referencias inexistentes y ciclos. Límites: 64 KiB, ocho oportunidades y cuatro objetivos. La generación se limita por instrucciones a una o dos oportunidades y un objetivo para acotar tokens y coste.

La preparación y las pistas no descubiertas se almacenan privadamente en `adventureModule`. Los invitados reciben una vista derivada con etiquetas disponibles, pistas confirmadas, objetivos y conclusión únicamente cuando procede. Las consultas reglamentarias no reciben el módulo privado. El anfitrión conserva acceso administrativo y exportación. Los documentos son datos de partida, no instrucciones de ejecución; el renderizado escapa HTML.

La importación de campaña comprueba también la coherencia de las pistas, su orden de requisitos, los intentos y el estado de objetivos. Se conserva la reanudación. No se borra ni sustituye una aventura activa mediante una respuesta del modelo. La importación de un módulo se realiza al empezar; la importación de campañas completas conserva su advertencia previa de sustitución.

## Coste y pruebas

Iniciar consume una intervención de IA y una confirmación. Interpretar una declaración libre usa la intervención narrativa ya solicitada. Las búsquedas directas y sus efectos no generan inferencias ni búsquedas remotas en manuales; cada búsqueda se guarda en una sola acción. Elegir 20 no hace veinte llamadas ni veinte escrituras. La narración de resultados se solicita explícitamente cuando es útil.

Pruebas: éxito, fallo y reintento, elegir 10/20 sin RNG, requisitos, datos adulterados, permisos, ausencia de pistas ocultas en el estado público, persistencia, exportación/importación, generación inválida, doble envío y conservación de fichas. La suite completa de 163 pruebas pasó con el emulador oficial, sin omisiones; después se comprobaron los cambios finales de validación con las pruebas afectadas. Playwright recorre importación JSON errónea sin envío, aventura aportada, pistas, conclusión, continuación, recarga y móvil. La calidad semántica de las generaciones reales se evalúa por separado.

La primera verificación de generación real encontró respuestas rechazadas sin instalar módulos parciales. Un diagnóstico posterior identificó campos de investigación indebidos en la apertura; el siguiente rechazo señaló propuestas de adjudicación manual. Se separaron los esquemas por operación y se consolidaron instrucciones antes de una nueva comprobación. Las aperturas solo pueden producir narración, memoria y módulo, sin decidir acciones del jugador. La salida se limita a 4.500 tokens al generar un módulo y a 3.000 en las demás intervenciones; es un máximo, no una medida de consumo real. Los fallos exponen una etapa segura sin mostrar claves ni el payload privado. No se puede certificar el origen del primer error genérico ni atribuirlo al límite de tokens sin evidencia.

Una comprobación posterior detectó referencias de objetivos inválidas. La generación ahora usa un contrato intermedio más pequeño: el modelo aporta la ficción y dos búsquedas; el código asigna identificadores, dependencias secuenciales y objetivo final. No se pide a la IA construir referencias que puede gestionar el motor. Las CD permitidas por el esquema se acotan a valores alcanzables por el grupo. Los módulos aportados conservan sus propios grafos validados; la generación breve actual tiene dos búsquedas enlazadas y no se presenta como una aventura arbitraria de varias escenas.
