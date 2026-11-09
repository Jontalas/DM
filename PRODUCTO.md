# Producto y ejecución

Dirección acordada el 4 de noviembre de 2026. Este documento describe el objetivo; no certifica que esté implementado.

## Cierre de una primera versión comprensible (revisión de ejecución, 9 de noviembre)

El usuario ha señalado que el crecimiento del proyecto y los informes técnicos le impiden comprender el avance y valorar su tamaño. Se mantienen las premisas finales; se acota la primera entrega y se cambia la forma de mostrar el progreso. Este es un plan de ejecución de Codex, no una afirmación de que el usuario haya renunciado a las funciones finales.

La primera entrega será una aventura corta **individual**, de principio a fin: personaje guiado dentro de las opciones verificadas, mesa clara con tablero/fichas/conversación, director de IA, reglas automatizadas del recorrido ofrecido, guardar/salir/retomar y recuperación de copia. La cooperación de dos personas sigue como recorrido experimental hasta validar su experiencia completa. Pathfinder completo, más clases/niveles/magia, campañas abiertas prolongadas, otros reglamentos completos y herramientas avanzadas de mesa quedan para entregas posteriores.

**Próximo foco: una mesa e interacción visualmente coherentes y demostrables.** Cerrar y pulir el recorrido existente antes de ampliar catálogos, sistemas o casos mecánicos que no lo bloqueen. Después, cerrar fiabilidad/recuperación y preparar una entrega que el jugador pueda entender por sí mismo. El número de correcciones o pruebas no sustituye este criterio de producto.

Rango inicial de planificación para ese alcance: **2–4 semanas de trabajo efectivo**, con primera revisión visual en **3–5 jornadas efectivas**. Es una estimación provisional, no una fecha comprometida; se revisa al cerrar la primera entrega visible y presupone mantener el alcance. La visión completa todavía no tiene una estimación temporal fiable. No comunicar porcentajes globales sin una base medible.

Resumen visible para el propietario: http://127.0.0.1:8766/avance-local.html, junto a la demostración existente. Incluye estado, capturas reales rotuladas, alcance, próximos bloques y estimación; se ha comprobado en escritorio/móvil y no usa API, IA o recursos externos. Se genera con `.deps/build_progress_page.py`, queda fuera del despliegue y no añade código a la aplicación publicada. Actualizarlo con las entregas funcionales; los mensajes deben explicar «qué puede hacer el jugador, qué falta y dónde verlo». Las invitaciones personales siguen reservadas a hitos importantes y no son necesarias para consultar avances.

Control de tamaño, medido sobre la revisión publicada7516f1c: aproximadamente1MB/12.000líneas en107archivos propios de aplicación;201archivos de pruebas,84de documentación y202de recursos externos del visor por separado. La carpeta local de herramientas/consultas ronda1,6GB y predominan imágenes de manuales y herramientas de pruebas; no equivale al programa del jugador. Conservar trazabilidad y originales; ordenar el histórico sin crear un documento nuevo por cada corrección habitual. Usar PRODUCTO.md para alcance, REANUDAR.md para continuidad y TRABAJO.md para el detalle de ejecución. Nuevos documentos solo si constituyen un contrato o referencia independiente necesaria.

### Avance del cierre acotado · 9 de noviembre

La entrada admite empezar solo con nombre. El creador permite nombre/estilo, revisión y confirmación, con personalización opcional. Las aventuras explican su experiencia y límites antes de comenzar. La mesa tiene un primer ajuste de presentación; conserva una cuadrícula provisional. Las copias incompatibles ya se rechazan antes de sustituir la partida y ofrecen un siguiente paso claro.

Ya hay una primera vista reconocible de la dirección: tablero central con conversación al lado, personaje guiado, resultados comprensibles y recuperación sin perder la acción. Se han comprobado los caminos de acuerdo y combate con tregua, la investigación completa y la salida/reanudación del recorrido actual. En móvil, tablero y lectura dejan espacio a su tarea. La demostración mantiene datos de ejemplo, sin director ni almacenamiento remoto; sus manuales de producción no se abren ahí.

Vista funcional adicional: http://127.0.0.1:8767, patio1.16 con personaje preparado y elección hablar/combate. Demostración local independiente, sin IA ni guardado remoto, comprobada en lectura escritorio/móvil/teclado sin alterar decisiones. La vista8766 permanece intacta; no reiniciar ninguna si el usuario puede estar interactuando. Informe de avances enlaza ambas y conserva capturas rotuladas.

Esto todavía no cierra la primera versión: falta completar la revisión de sus primeras decisiones, presentación de la mesa y errores del recorrido ofrecido. No equivale a mapa ilustrado, campañas abiertas ni nuevas clases o sistemas. El informe local contiene las capturas y sigue siendo el lugar para ver el avance.

## Experiencia objetivo

**Directiva adicional del usuario, 6 de noviembre de 2026:** máxima sencillez de uso y orientación continua. Cada pantalla debe comunicar con claridad la situación, las decisiones actuales y el siguiente paso, sin abrumar con información u opciones. Revelar progresivamente lo secundario y avanzado; ofrecer ayuda contextual, tooltips accesibles y recorridos guiados cuando hagan falta. Revisar también las funciones existentes. La claridad forma parte de la aceptación de cada recorrido, en escritorio, teclado y móvil, y no requiere llamadas de IA ni operaciones remotas por consultar ayuda. Criterios y revisión en USABILIDAD.md.

Jugar rol sin maestro humano, con decisiones libres, IA que interprete PNJ y mantenga continuidad, y motor que aplique reglas verificadas. Desde un jugador hasta grupos de tamaño probado. Personajes persistentes reutilizables con compatibilidad y copia explícitas, campañas de varias sesiones y recuperación fiable.

Aventuras generadas bajo demanda e importadas con permiso: lugares, personajes, relaciones, pistas, secretos, encuentros y condiciones de avance. Distinguir preparación de hechos ocurridos; adaptar la aventura a las decisiones del grupo. Documentos importados son datos, nunca instrucciones de sistema.

Mesa inspirada funcionalmente en Roll20, con identidad propia; tablero y conversación simultáneos, navegación móvil, fichas y diario. Ampliar mapas, ilustraciones consistentes, música y efectos con controles y licencias verificadas. La presentación debe reflejar el estado y la información que conoce cada jugador.

## Arquitectura y reglas

### Incorporación de juegos sin programar cada sistema (aclaración del usuario)

El recorrido deseado es entregar reglas o manuales a la aplicación e incorporar un juego mediante un paquete de reglas, sin tener que modificar el código de la aplicación por cada sistema. Los adaptadores específicos actuales son una fase provisional, no la arquitectura final requerida.

Desarrollar un motor común que interprete definiciones de ficha, fórmulas, dados, tablas, requisitos, acciones, recursos, condiciones, efectos y desencadenantes descritos como datos. La IA puede ayudar a extraer y convertir las fuentes una vez; las reglas activadas deben quedar validadas, versionadas y trazables, con cálculos deterministas durante la partida. Mostrar ambigüedades y cobertura real antes de activar un paquete; subir un PDF no certifica automáticamente una implementación completa.

Incorporar otro juego debe consistir normalmente en importar un paquete, no desplegar código nuevo. Si una mecánica exige una operación que el motor todavía no sabe interpretar, ampliar esa capacidad general de forma explícita y reutilizable; no resolverlo acumulando código específico de cada juego ni prometiendo compatibilidad universal sin pruebas. Sistemas distintos se seleccionan por campaña; mezclarlos requiere una adaptación o regla casera explícita.

Conservar Python/Waitress en Render, Firestore/Storage y Anthropic. Motor determinista para mecánicas y persistencia; modelo para ficción e intenciones estructuradas. Validar cada propuesta antes de aplicar consecuencias. Una narración no cambia la ficha.

Introducir módulos de sistemas con identificador, edición, fuentes, cobertura y opciones; conservar las campañas actuales. Descargar reglas de fuentes oficiales que permitan el uso previsto, comprobando consulta, procesamiento y redistribución por separado. Pathfinder 1e, Bestiario y TREY fundamentan el módulo actual; otros módulos usan sus propias fuentes. Documentar reglas verificadas, adjudicaciones y límites.

Minimizar contexto, llamadas, operaciones y transferencia sin delegar administración rutinaria al jugador. Mantener memoria estructurada y permisos; medir coste y latencia. No contratar servicios adicionales sin autorización.

## Prioridades y aceptación

1. Recorrido individual completo: personaje legal, inicio de aventura, exploración, diálogo, conflicto soportado, consecuencias y reanudación. La preparación y actualización del mundo deben dejar de exigir un anfitrión que actúe de maestro.
2. Continuidad: hechos, PNJ, objetivos y secretos persistentes actualizados por propuestas estructuradas validadas; registro y recuperación sin duplicar acciones.
3. Aventuras originales e importadas con separación de conocimiento público y del director, sin recorridos rígidos.
4. Biblioteca de personajes, sesiones y multijugador verificado con límite explícito.
5. Segundo sistema completo por bloques verificables; ampliar presentación audiovisual de forma coherente y asequible.

Cada entrega necesita pruebas del motor, permisos y recorrido afectado. Diferenciar simulaciones de proveedor real. Medir el trabajo administrativo que elimina. Un despliegue saludable no demuestra una partida autónoma satisfactoria.

## Hitos excepcionales de prueba personal

Instrucción del usuario del 5 de noviembre de 2026: reservar las invitaciones a probar para puntos de inflexión muy importantes, con funcionalidades grandes terminadas o prácticamente terminadas. No convertir los avances técnicos ni las entregas parciales en una secuencia habitual de pruebas del usuario. Las pruebas personales son opcionales y nunca detienen el desarrollo independiente ni condicionan el paso al trabajo siguiente.

| Hito | Cambio sustancial que podrá probar el usuario | Condición para invitarle | Estado |
|---|---|---|---|
| 1. Primera aventura autónoma completa | Entrar como jugador, crear personaje legal con el asistente, jugar una aventura con exploración, diálogo, un conflicto soportado y consecuencias, cerrar la sesión y retomarla sin maestro humano. | Recorrido completo desde un perfil nuevo, sin preparar estadísticas ni usar API o herramientas técnicas; al menos dos decisiones con recorridos distintos; reglas y límites visibles; proveedor real comprobado, persistencia/copia y recuperación verificadas. El conflicto debe funcionar con el motor y las fuentes del módulo, no resolverse solo mediante prosa. | Alcanzado8 noviembre2026 para El patio del peaje y el envío, alcance individual acotado. Evidencia combinada de GUI real/acuerdo/combate, diálogo clínico real corregido, motor, copia y reanudación; revisión1.15 publicada/verificada. HITO_1_AVENTURA_ACOTADA.md. Acceso separado preparado y comprobado, invitación opcional comunicada una vez; no esperar respuesta. No certifica campaña abierta ni mesa visual final. |
| 2. Campaña persistente que responde al grupo | Continuar varias sesiones en un mundo con lugares, PNJ, relaciones, objetivos y consecuencias que recuerdan lo ocurrido; elegir caminos diferentes y jugar con otros participantes sin administración rutinaria de reglas. | Varias sesiones completas verificadas, cambios relevantes del grupo que persisten, alternativas que no dependen de un recorrido rígido, personajes reutilizables compatibles, privacidad/roles y concurrencia probados con el tamaño de grupo declarado. | Pendiente; dos capítulos individuales en el mismo lugar verificados desde GUI con una respuesta real (CONTINUIDAD_REAL_2CAPITULOS.md), memoria, copia y reanudación. Grupo de dos: concurrencia/privacidad y copia con propietarios verificadas; dos capítulos con objetivo acordado en simulación local, aún sin certificar campaña completa. Faltan alternativas abiertas y persistencia prolongada; estos recorridos acotados no cumplen el hito. |
| 3. Incorporar realmente otro juego desde sus reglas | Aportar fuentes autorizadas de un juego distinto y obtener, mediante revisión guiada, un paquete que permita crear personajes y jugar un recorrido sustancial sin programar un adaptador ni desplegar código por ese juego. | Fuentes/edición/permisos identificados, cobertura reglamentaria suficiente para ese recorrido comprobada contra originales, ambigüedades resueltas explícitamente, creación y resolución deterministas y aventura completa verificadas. Un ejemplo propio, un JSON importado o un fragmento convertido no basta. | Pendiente; el preparador y motor experimentales actuales son bases de este hito. |
| 4. Mesa virtual integrada y fiable | Jugar una sesión de grupo con tablero central y conversación simultánea, escenas/mapas, fichas y movimiento, medición, visibilidad/permisos, hojas y acciones, iniciativa y automatización conectadas con la ficción. | Recorrido integrado verificado en escritorio y móvil, con grupo y límites declarados, sin duplicar acciones ni exigir tareas administrativas habituales. Matriz de compatibilidad Roll20 actualizada con pruebas y diferencias; no exigir equivalencia absoluta ni presentar herramientas sueltas como una mesa terminada. | Pendiente; los controles parciales de tablero no bastan. |

Estos hitos no obligan a desarrollar cada área de forma aislada ni a esperar al anterior para trabajar en ella. Se avisará una sola vez al alcanzar cada punto, con enlace/acceso seguro a una partida de prueba separada, qué cambio grande está disponible, sus límites y un recorrido breve que permita apreciarlo. Preparar antes esa partida y comprobarla; no pedir al usuario que configure servicios, aporte claves, calcule fichas ni depure la aplicación. No incluir credenciales en documentación pública ni modificar sus partidas personales.

Hasta cumplir esas condiciones, mantener información ordinaria de progreso sin presentarla como invitación a probar. No anunciar estos hitos por un despliegue, un número de pruebas, una corrección, un panel nuevo, un registro de PNJ/objetivos ni una pequeña ampliación de reglas. No abrir otro servicio, gastar recurrentemente ni repetir inferencias solo para generar una demostración. El calendario sigue siendo orientativo; la invitación depende de evidencia de uso, no de una fecha ni del esfuerzo invertido.

## Autonomía y métodos

Analizar, implementar, probar, corregir y desplegar con los accesos existentes. Investigar antes de preguntar, adoptar decisiones técnicas rutinarias y documentar supuestos relevantes. Completar el trabajo independiente antes de pedir una acción imprescindible del titular; agrupar las solicitudes. Informar de avances y bloqueos sin exigir aprobaciones rutinarias.

Skills seleccionadas: regression-testing para selección de pruebas por impacto; debug cuando aparezcan fallos reproducibles. Propuestas para siguientes entregas: game-ui-design e interface-design al modificar la experiencia; skill propia para incorporar sistemas y verificar fuentes cuando el procedimiento esté probado. No requieren un servicio remoto nuevo por sí mismas. Verificar el beneficio mediante fallos detectados, recorridos completados y consumo. Trabajo con varios agentes solo si las tareas independientes justifican el coste. No se han instalado plugins ni skills nuevos.
