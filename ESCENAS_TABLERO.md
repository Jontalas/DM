# Tableros por escena y continuidad del patio

Trabajo local en desarrollo,7 de noviembre de2026. Producción44e59e7bd28da9f57c7a9aa87d01c930a0cab45d, Render7615269069 success, revisión exacta/salud HTTPS verificadas. Incluye guía y tiradas claras; separación de tableros aún no publicada ni ofrecida por una aventura.

**Actualización local1.4:** ruta original implementada y verificada por navegador, todavía sin publicar. Patio→almacén directo o cobertizo opcional con regreso al patio; cada camino localiza el mismo envío. Fichas, hallazgos, posiciones recordadas y encuentro original se conservan. Recibo2 vincula ruta original; guardiana permanece en patio, actor en lugar actual. Versiones1.0–1.3 intactas y solicitudes antiguas sin versión siguen1.0. Descriptor local ya1.4; producción aún1.3.

55 pruebas afectadas y cuatro HTTP/Waitress correctos, incluido commit503, cliente Firestore nuevo, duplicado, ida/vuelta, final, copia, invitado sin preparación y rechazo de guardiana trasladada. Solicitudes del director se limitan a actores presentes. Navegador completo por acuerdo/ruta opcional/regreso y combate/ruta directa: creador legal, ataques reales del motor, sin editar PG ni preparar fichas, diario de lugares conocidos, copia por interfaz/recarga y móvil. Capturas privadas pf-route-parley/combat-board/journal-mobile.png revisadas. Se muestra «Hora no registrada» cuando el reloj inicial carece de avance calculado; el dato original se conserva, sin inventar tiempo. Diario marca ruta completada según progreso confirmado.

Regresión: encuentro y auxilio, continuidad1.3 fijada explícitamente en fixture, rutas anteriores, recuperación compartida y corrección médica correctos. Suite completa terminada: **659 pruebas correctas sin omisiones (301,479 s)**, .deps/pf-scene-boards-route-final-tests.log. Backend sin cambios desde inicio de suite; después solo presentación de hora/estado y pruebas/capturas correspondientes. Guion privado .deps/verify_pf_route_live.py preparado/compilado, no ejecutado: nueva campaña técnica y máximo una solicitud de continuación al terminar ruta, con reserva persistente y negativa a repetir sesión. Es distinto del ensayo1.3 ya verified, que no se repite.

## Referencia y adaptación

Consulta documental del7 de noviembre a [Page Menu & Folders](https://help.roll20.net/hc/en-us/articles/360039675413-Page-Menu-Folders), actualización indicada16 de septiembre de2026: una partida contiene páginas; la página que ve el grupo se gestiona separadamente de la copia de fichas entre páginas. Se documenta acceso del GM, gestión de páginas y herramientas del grupo. No se abrió una sesión interactiva de Roll20 ni se inspeccionó código privado.

Consulta complementaria a [Creating Pages and Adjusting Page Settings](https://roll20partners.zendesk.com/hc/en-us/articles/10269611754775-Creating-Pages-and-Adjusting-Page-Settings): el artículo señala que sus controles antiguos tienen una referencia más reciente, que se siguió al documento anterior. La Wiki Page Menu devolvió403 al acceso directo; no se utiliza como evidencia completa.

Adaptación propia: el jugador elige una salida narrativa disponible y el motor cambia el contexto de tablero dentro de esa misma acción. No exige administrar una cinta de GM. Conserva al PNJ en su localización y recuerda posiciones/terreno de lugares visitados. El cambio es un enlace narrativo declarado: no calcula distancias, duración, viaje con peligros ni curación. No equivale todavía al menú completo de páginas, grupos divididos, mapas gráficos, capas o visibilidad de Roll20.

## Contrato local implementado como base

board_scenes.py es puro, sin IO ni dados. Campañas sin boardScenes conservan comportamiento anterior. Al activarse, cada ficha tiene sceneId; el tablero actual mantiene su terreno y se archivan los demás visitados con nombre, terreno y posiciones recordadas. Cambiar lugar requiere salida autorizada por el llamador y un PJ presente de PG positivos; pendientes, condiciones o pacientes negativos impiden omitir seguimiento. Cambia posición de entrada por elección explícita de salida, conserva salud y combatSerial global, y recuerda posición al regresar. Aún no hay acción pública genérica para activar/cambiar páginas.

Iniciativa, ocupación, movimiento, objetivos, flanqueo y tácticas se restringen a participantes presentes. Participantes ausentes no se pueden mover o atacar desde otro tablero. Un paciente/condición fuera de escena bloquea nuevas acciones que puedan omitir su seguimiento. Administración y consulta de ficha siguen disponibles para correcciones explícitas. El encuentro original no se reinicia ni aplica su recuperación a combates de otro lugar.

Importación valida ámbito, identidades, coordenadas, terrenos, archivos visitados e iniciativa. Edición avanzada conserva sceneId. El cliente filtra tablero, lista de movimiento, objetivos y gestos; el grupo conserva acceso a fichas conocidas con indicación «En otra escena». Título del tablero muestra la localización y se retiran previsualizaciones al cambiar de lugar. No hay nuevas lecturas/escrituras por seleccionar, medir o arrastrar.

## Verificación y siguiente paso

12 pruebas nuevas de base/motor y74 afectadas correctas. Cubren ida/vuelta, terreno/posición, época global, validación de copias, acciones remotas rechazadas antes de dados, iniciativa local, flanqueo y tácticas. Un fallo de organización del archivo de pruebas se corrigió y se repitieron correctamente. Falta integrar y probar por HTTP/navegador la ruta real1.4; no anunciarla como implementada ni desplegar este bloque aislado como recorrido terminado.

Siguiente: definición1.4 y ruta original con patio, cobertizo opcional y almacén; conservar1.3. Recibo de continuidad nuevo vinculado a ruta original; cada investigación/cambio revalida participantes, guardiana en patio, archivo de escenas y progresos. Confirmar persistencia/copia/cliente nuevo y regresión antes de publicar. Mantener pendientes calendario/descanso completo, peligros de viaje, capas/visibilidad y campaña larga.

Los «siguientes» anteriores describen la secuencia de construcción de la base; prevalece la actualización local1.4 superior. Numeración de cada cambio de contexto contrastada visualmente con TREY original PDF/folio12, reutilizando adventure_routes.py. No se conceden FH por volver a un lugar. Las investigaciones reutilizan Percepción/elegir10/20 ya verificados en Reglas PDF87/101; no se añaden fórmulas ni CD oficiales inventadas. No hay acceso a menú general de páginas, grupos separados, imágenes o visibilidad.
