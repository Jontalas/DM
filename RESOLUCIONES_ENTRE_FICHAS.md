# Resoluciones entre fichas: kernel y siguiente integración

Capacidad `target-sheets` y recorrido local optativo `abstract-scene-targets`, pendiente de despliegue. No implementa combate espacial ni Pathfinder. El ejemplo propio CC0 usa dos recursos abstractos; sus números no se atribuyen a un manual.

Validación del kernel: 458 pruebas completas con emulador correctas sin omisiones (176,761 s), incluidas cinco pruebas nuevas de dos fichas/condiciones/origen simultáneo/ciclos/aislamiento. Navegador normal con acción de objetivo oculta correcto; captura original antigua revalidada sin red ni inferencia. Desarrollo en feature; no desplegar como ataque utilizable hasta terminar la siguiente integración y su proyección privada/pública.

## Recuperación y presentación integradas localmente

`introducedAt` marca el primer índice mecánico disponible al preparar actores nuevos, sin mensaje público que anuncie actores ocultos. Los actores antiguos sin esa marca siguen válidos en su recorrido anterior; una resolución dirigida no puede atribuirles una cronología inventada.

`targetResolutions` conserva como máximo 128 pruebas privadas y 256.000 bytes, con índice de mensaje, referencia de ambas revisiones, entradas y traza completa. La recuperación reconstruye fichas de jugadores y actores desde sus creaciones, intercala acciones individuales y dirigidas, verifica ambas revisiones y sus estados finales, y rechaza referencias anteriores a la preparación del objetivo. Los metadatos de creación pueden verificarse por separado, pero nunca bastan para aceptar una ficha evolucionada: se compara también el resultado completo del registro privado. Una copia mantiene el controlador de PNJ y reasigna únicamente los personajes de jugadores.

El cliente no recibe el registro ni las fichas/trazas privadas de actores. El mensaje público conserva solo su traza propia y targetRef con identidad/PNJ, mostrado como objetivo de la acción. La política inicial rechaza que cantidad, caras o condición de dados públicos dependan de un campo no compartido del objetivo; aún no implementa dados privados adicionales. No pretende impedir toda inferencia posible a partir de resultados legítimos del juego.

El contrato optativo `rule-pack-director-target-facts-5` da a la continuación identidad, campos compartidos y cambios publicados tanto en esa resolución como ahora, más los hechos propios del jugador. El registro conserva sharedFields como fotografía de esa publicación; no revela valores históricos al publicar un campo posteriormente. Los textos largos se omiten con huella. En modo abstracto informa si sigue acreditándose percepción compartida, sin revelar la ubicación privada ni la causa de perder contacto. No publica HP, condiciones ni estadísticas privadas como si fuesen conocidas. La continuación debe corresponder al último resultado mecánico. El historial posterior conserva la referencia pública del objetivo sin la prueba privada. El conversor de manuales excluye ambas capacidades hasta que su preparador admita ejemplos completos con dos fichas; su clave de captura sigue basada en la solicitud original.

Comprobado con proveedor simulado: HTTP/Waitress de importación/privacidad/continuación/copia, navegador anfitrión/invitado/móvil, nombre de objetivo escapado, campos compartidos y una continuación, sin llamadas remotas por consultar. No se han hecho nuevas inferencias reales. Suites completas sucesivas: 466 (175,511 s), 467 (201,238 s) y 476 pruebas (191,363 s) correctas sin omisiones; validación final tras publicación histórica y contexto de percepción en ejecución.

## Recorrido explícito de escena abstracta

Validación final integrada: **478 pruebas completas con emulador correctas sin omisiones (216,111 s)**, registro .deps/target-final-tests.log. Navegador explícito de acciones confirmado de nuevo; vista local del selector sin acciones al consultar. Pendiente despliegue/verificación remota en este punto.

La acción declara targetContext:{kind:abstract-scene,sceneField:id,visibleField:id,turns:not-required} y requiere abstract-scene-targets. Los campos de escena deben ser texto no vacío e idéntico; el campo de percepción común del NPC, booleano true. Otras clases de contexto, alcance espacial e iniciativa se rechazan, sin equivalencias inventadas. No sustituye percepciones individuales ni visibilidad táctica.

La proyección targetOptions agrupa candidatos por personaje propio y par de campos de contexto, evita duplicarlos por cada acción y no contiene fichas ni valores privados. Solo usa datos cargados. No elige un objetivo ni acredita todos los requisitos de una acción: éstos se comprueban al prepararla y nuevamente antes de tirar.

El selector de interfaz permite elegir explícitamente personaje, acción y PNJ. Cargar opciones/cambiar de herramienta conserva un borrador local; no usa IA ni escribe estado. request_pack_target crea la solicitud y registra lo elegido, sin ejecutar consecuencias ni llamar al modelo. resolve_pack_request valida identidad, contexto, requisitos y ambas revisiones, calcula una secuencia de dados y confirma fichas, traza pública, evidencia privada y barrera en un lote. La semilla duradera ya existente cubre los dados del servidor; HTTP/Waitress comprueban fallo de commit y recuperación con cliente Firestore nuevo. El recorrido normal del navegador continúa el relato una sola vez tras confirmar; proveedor simulado, interpretación del objetivo por IA no necesaria.

Este modo exige perfiles de NPC preparados y no añade todavía su creación automática al importar aventura. El texto libre del director no propone estas acciones: se eligen en el selector para conservar agencia y ahorrar una llamada de interpretación. Vincular objetivos de aventura o descubrimientos a otro actor sigue pendiente y se rechaza explícitamente; no se cierran por un éxito sobre el NPC equivocado. No hay turnos automáticos de NPC, reglas de combate espacial ni cobertura nueva certificada de manuales. Ningún hito excepcional de prueba personal se considera alcanzado.

## Contrato matemático implementado

Una acción declara `target:true`. Sus expresiones pueden consultar `target.campo` mediante el formato normal de referencias; los efectos usan `scope:target` para escribir en la otra ficha y `scope:self` (u omisión) para escribir en quien actúa. Un campo se puede asignar una vez por ámbito. Las etapas de creación no admiten objetivos externos. Las dos fichas tienen que pertenecer al mismo contenido exacto de paquete y haber completado su perfil.

`preview_targeted` valida requisitos y dados sin tirar. `execute_targeted` calcula una sola secuencia de dados y devuelve las dos fichas más la traza completa. Todos los efectos iniciales leen las dos instantáneas originales; el orden de aplicación no convierte un efecto en entrada implícita del siguiente. Después se resuelven por separado los desencadenantes de cada ficha hasta estabilidad, bajo presupuesto y detección de ciclos. Una excepción no modifica ninguna de las fichas originales. Cada resolución incrementa las dos revisiones, aunque un fallo no cambie campos del objetivo; revisión no significa daño ni paso de tiempo.

La traza de quien actúa mantiene sus cambios, dados, fuentes, desencadenantes y salidas declaradas; `trace.target` contiene revisión anterior/posterior y cambios/desencadenantes del otro lado. Es evidencia privada de resolución: no debe enviarse íntegra al cliente. El kernel no decide propietarios, identidad física, selección, ubicación, visibilidad, alcance, turnos ni adjudicaciones del juego. Lo que puede resolverse depende de las fórmulas y cobertura verificadas del paquete.

La ruta individual rechaza acciones con objetivo antes de tirar. El selector separado admite únicamente el contexto abstracto conectado; el director de texto libre y la preparación automática siguen excluyéndolas. Los paquetes anteriores conservan los mismos contratos y trazas. El cierre de un objetivo de aventura solo puede usar un resultado booleano propio de la acción, no un efecto de igual nombre sobre otra ficha.

## Integración actual y ampliaciones pendientes

1. Solicitud y selección conectadas para escenas abstractas compartidas explícitas. Ampliar presencia/visibilidad/alcance y turnos por capacidades verificadas; nunca asumirlos por conocer el nombre del NPC.
2. Cronología implementada para actores nuevos y comprobada al recuperar y resolver. No migrar actores antiguos inventando su fecha de preparación.
3. Registro privado, reproducción y comparación final conectados al guardado de la nueva acción. No presentar metadatos de creación como prueba suficiente del estado final.
4. Confirmación conjunta y semillas conectadas, con fallos de commit/cliente nuevo comprobados. Ampliar concurrencia y recuperación cuando haya cambios intermedios de versión, sin permitir nuevas tiradas por reintentos.
5. Publicar únicamente el resultado permitido: el registro privado puede contener campos o modificadores ocultos. Examinar también si cantidad, caras o condición de una tirada dependen de un campo privado del objetivo; no filtrar valores mediante su forma. Hasta disponer de una política de visibilidad, limitar los casos ofrecidos explícitamente.
6. Continuación y hechos públicos conectados con contrato optativo; validación real del proveedor aún pendiente. Copiar, recuperar o consultar no requiere inferencia. Usar presupuesto cerrado y no repetir sesiones fallidas para buscar una aceptación favorable.

No introducir valores de CA, daño, alcance, iniciativa o clases del módulo Pathfinder en el kernel. Antes de construir su paquete de conflicto, verificar cada regla pertinente contra Reglas básicas/Bestiario y las excepciones; PNJ_FUENTES.md solo documenta una primera consulta del creador. La selección local y los cálculos se resuelven sin operaciones remotas adicionales.
