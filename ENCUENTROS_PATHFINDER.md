# Encuentro preparado del módulo Pathfinder

Estado: encuentro acotado integrado localmente, **todavía sin desplegar**. Incluye acuerdo, combate, primeros auxilios y desenlace; no es un hito de aventura autónoma. El bloque de captura Pathfinder precedente está desplegado en `3168478`, con revisión y salud HTTPS verificadas.

`adventures/pf-patio-del-peaje.json` es una escena original, no ficción del Bestiario. `pf_encounters.py` la enlaza con la plantilla publicada `pf1-goblin-warrior-1`. No acepta estadísticas del jugador ni convierte reglas de otros sistemas. La definición 1.0.0 queda fijada por su hash al entrar y al recuperar una copia; versiones futuras deben conservar esta definición y añadir una nueva, no reinterpretar partidas anteriores.

## Recorrido implementado

Desde una campaña nueva, el jugador crea el PJ con el asistente y consulta la escena. Entrar prepara automáticamente la guardiana y conserva la ficha/posición del PJ; muestra la situación y deja pendiente la decisión. No tira iniciativa ni inicia hostilidades por entrar. Solo el propietario elige por ese personaje, incluso ante otro anfitrión. La conversación libre con el director sigue disponible por el recorrido existente; este inicio escrito no necesita una llamada al modelo.

Dos decisiones explícitas:

- Hablar y proponer el paso: la respuesta voluntaria escrita de este PNJ concede permiso, sin elegir palabras del PJ, mover su ficha, descontar objetos ni convertirlo en una regla general de Diplomacia. La fase es `agreement`, no un resultado de dados.
- Entrar en combate sin sorpresa: reutiliza el combate, iniciativa, desempates, turnos automáticos de adversarios, ataques y persistencia existentes. El motor no elige acciones del PJ. Si este inicia después combate por las herramientas de mesa, la fase también refleja ese cambio.

No se mezclan estas fases con el módulo de investigaciones tranquilas. El recorrido inicial exige un solo PJ del creador sin correcciones, con PG máximos y sin condiciones, tablero nuevo sin terreno ni combate previo, posición inicial y ninguna solicitud pendiente. No cura ni teletransporta un PJ para cumplir requisitos. La escena declara iluminación normal, espacio abierto y percepción mutua; no implementa sorpresa, oscuridad, ataques a distancia ni poderes adicionales de la criatura.

## Fuentes y autoridad

Se reutilizan los datos/huellas/avisos de `npc_catalog.py`, sin cambiar cálculos ni crear un goblin como si fuera un PJ humano: Bestiario Devir PFR002, PDF167/folio166 y PDF7/folio6; espada corta Pequeña y crítico en Reglas básicas PDF143/folio142 y PDF185/folio184. Iniciativa y control táctico son los del motor ya documentado en COMBATE.md y MESA_VIRTUAL.md. La copia conserva controlador `director`, procedencia y licencias OGL mediante los mecanismos existentes.

Reglas básicas PDF191/folio190 revisada de nuevo en el original local: morir exige PG negativos iguales a Constitución; un moribundo sigue perdiendo PG y dispone de estabilización por turno. No existe aquí una excepción verificada que convierta 0PG de un PNJ en muerte. El encuentro **no concluye automáticamente por 0PG ni por una frase del modelo**. El navegador ha verificado un ataque que deja al PNJ negativo pero por encima de su umbral de muerte, manteniendo combate y desenlace pendientes.

## Evidencia y coste

Cinco pruebas de preparación/elección/copia y dos HTTP/Waitress correctas, sin proveedor. Navegador desde bienvenida y creador, dos salas con decisiones distintas, PNJ preparado, iniciativa automática, ataque real del motor, copia/permisos y móvil; cero llamadas de IA. No se escriben estadísticas manualmente ni se hace `create_npc` desde el cliente. La consulta del descriptor es local al servidor y no accede a Firebase; cada elección usa una acción transaccional normal. Los dados del combate pasan por la reserva duradera existente, sin otra llamada de IA ni nueva fórmula de reglas.

## Siguiente trabajo imprescindible

Completar recuperación horaria, asistencia adicional y continuidad tras combate antes de presentar una aventura autónoma o invitar al usuario a probar un hito. Conservar las heridas y las decisiones de jugadores conscientes. Verificar en originales el tiempo y requisitos de cualquier recuperación; no inventar curación ni consciencia. Retirada, recompensas/PX, siguiente escena, combate completo y grupos mayores siguen fuera de la cobertura actual.

## Primeros auxilios y desenlace incorporados después

Cierre de verificación: **574 pruebas completas con emulador correctas, sin omisiones (127,479s)**, `.deps/pf-encounter-release-final-tests.log`; catorce específicas del módulo. HTTP y Waitress verifican además derrota por ataque automático, duplicado y copia. Se corrigió un avance de turno posterior al cierre del ataque. Navegador repetido tras el ajuste de mensajes, correcto. Cero inferencias reales nuevas.

Reglas básicas PDF93–94 y PDF191/folio190 comprobadas visualmente: primeros auxilios CD15, acción estándar, reintento mientras vive, estabilización sin recuperar PG. Se usa el total preparado de Curar y un d20 físico autorizado o virtual duradero. Se exige adyacencia, turno y acción disponible; actuar con 0PG conserva el coste de quedar a −1PG. El jugador también puede elegir explícitamente esperar sin ayudar; el motor procesa las pruebas normales de estabilización hasta estado estable o muerte, conservando cada tirada.

Discrepancia del original: el encabezado de Curar en PDF93 dice Int, mientras la tabla 4-3 de PDF90/folio89, las listas de clase y el apartado de Sabiduría indican Sab. Se conserva el total Sab ya preparado por el creador; no se atribuye una errata oficial ni una modificación nueva de característica. No se presupone material de sanador ni se añade su bonificación.

El enfrentamiento cesa automáticamente cuando el PNJ está muerto o inconsciente estable y el PJ sigue consciente. Los 0PG no disparan ese cierre. Si cae el PJ, la conducta original de esta guardiana es cesar ataques y esperar; esto es ficción de la escena, no una regla de Pathfinder. Se procesan las pruebas de los caídos hasta muerte o estabilización, sin curación ni decisiones por un PJ inconsciente. Se guardan PG, Constitución y ronda del desenlace para recuperar la copia sin reinterpretarlos. Condiciones, correcciones excepcionales y participantes adicionales quedan fuera de esta automatización.

Evidencia posterior: trece pruebas de preparación, auxilio, dados físicos/permisos, reintento, 0PG, espera, derrota con uno o ambos caídos y validación de copia correctas. HTTP/Waitress prueban primeros auxilios con fallo de commit, cliente nuevo y duplicado sin repetir dados. Navegador pasa acuerdo y combate desde creador, turno de moribundo, auxilio estándar, desenlace estable sin curación, recarga y móvil. La derrota tiene evidencia del motor, no todavía un recorrido de navegador propio. Suite anterior a la automatización de derrota: 569 pruebas correctas sin omisiones; no acredita por sí sola la última ampliación.
