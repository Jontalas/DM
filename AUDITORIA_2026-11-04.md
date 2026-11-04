# Auditoría inicial — 4 de noviembre de 2026

## Evidencia y alcance

Inspección de código y documentación, pruebas locales y dos consultas HTTPS de solo lectura. No se crearon partidas de producción, no se modificaron datos reales y no se realizó inferencia facturable.

Render respondió HTTP 200 en `/healthz` con `status: ok`. `/api/status` informó alojamiento Render, Cloud Firestore, Anthropic, modelo configurado `claude-haiku-5-5`, clave presente e índices de 102/577/329 páginas. Esto no confirma disponibilidad de inferencia, calidad narrativa ni revisión de código desplegada.

## Inventario

| Área | Evidencia actual | Límite para el objetivo |
|---|---|---|
| Mesa y multijugador | Tablero, fichas, conversación, permisos y sincronización por versión; pruebas HTTP y controles locales | Equivalencia completa con Roll20 no demostrada; falta probar tamaño máximo del grupo |
| Personajes | Creador determinista acotado, edición y pruebas de cálculos | No cubre todo Pathfinder ni biblioteca independiente entre campañas |
| Mecánicas | Movimiento, combate básico, adversarios y pruebas de personaje en módulos separados | Casos no cubiertos requieren adjudicación; no se puede afirmar ausencia de maestro humano |
| Director | Solicitudes reales a Anthropic y propuestas estructuradas; contratos con proveedor simulado | Sin evaluación real de una aventura completa; varias consecuencias y diario siguen dependiendo del anfitrión |
| Campañas | Estado persistente, exportación/importación y deduplicación | Memoria narrativa y actualización del mundo no completan el circuito autónomo |
| Reglas | Tres manuales privados, búsqueda y lector por páginas | Sin arquitectura multi-sistema completa ni incorporación de reglas públicas oficiales |
| Aventuras y audiovisual | Interfaz de mesa y diario | Sin importador estructurado de aventuras, generación persistente completa ni música/efectos |

## Primera mejora implementada localmente

Se añade preparación opcional `directorNotes` en el diario, editable solo por anfitrión. El contexto de narración la recibe como conocimiento del maestro; las consultas de reglas la excluyen. La vista de invitados la elimina. Los secretos antiguos y notas personales no se transfieren al proveedor. Se separa la construcción del contexto para comprobar estas fronteras sin consumir IA.

El cambio no migra secretos antiguos, no modifica reglas ni requiere otra operación remota o servicio. Añade al contexto únicamente la preparación introducida para ese fin. El anfitrión aún administra este campo; esta entrega no automatiza la preparación de aventuras ni el descubrimiento de hechos. Las instrucciones al modelo no garantizan que nunca revele un secreto: queda pendiente una evaluación real de filtraciones y continuidad.

## Verificación

Con `.venv`: 130 pruebas Python ejecutadas, 123 correctas y 7 omitidas por falta de emulador oficial de Firestore. Incluye el recorrido HTTP bajo Waitress y las nuevas comprobaciones de contexto y permisos. Existen advertencias ResourceWarning de respuestas HTTP en pruebas heredadas; la suite termina correctamente.

JavaScript: sintaxis de app.js, sincronización y 160.000 rutas geométricas correctas. Playwright pasó el recorrido de fichas, solicitudes, dados, dos sesiones y móvil. No se ha realizado inferencia real. La primera ejecución con Python global falló por dependencias ausentes; no era el entorno del proyecto.

## Siguiente entrega

Cerrar inicio y continuidad de una aventura individual: preparación estructurada generada por IA, hechos y objetivos persistentes validados, y narración que retome resultados del motor. Mantener pruebas de permisos, reenvíos y fallos, antes de ampliar sistemas y recursos audiovisuales. Especificación permanente en PRODUCTO.md.

## Publicación

Actualización: el usuario renovó la autenticación de GitHub. Una prueba de publicación fuera del aislamiento terminó correctamente. Se repitieron 46 pruebas afectadas con resultado correcto antes de preparar la publicación; el despliegue se verificará por HTTPS tras el envío.

Cambios locales aún sin desplegar. La consulta inicial del remoto Git falló con `SEC_E_NO_CREDENTIALS`; se recuperó la lectura usando OpenSSL y el certificado local .deps/windows-ca.pem. El remoto sigue en 455d5ec. Una prueba de publicación con `push --dry-run` falló: el gestor wincredman no pudo persistir credenciales y Git no pudo obtener usuario. No se dispone de credenciales Render en variables del proceso. Esto no afecta al trabajo local ni demuestra caída del servicio. No se han publicado cambios ni solicitado nuevos servicios de pago.
