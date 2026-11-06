# Plantillas de adversarios desde fuentes verificadas

Desplegado y verificado: d4816bd83d802777701f82dd831ce87e4509d1ec, Render7588288003 success y revisión/salud exactas. Preparación aislada de producción sin IA: valores publicados, controlador, duplicado, copia, invitado y avisos correctos; ninguna aventura iniciada. Navegador anfitrión/invitado/copia/móvil correcto, cero acciones por consultar. Los «pendiente/sin API» inferiores corresponden al proceso de construcción previo; sigue pendiente conectar un encuentro autónomo.

## Integración local posterior

API create_npc integrada y en validación final: anfitrión, datos de catálogo, fuera de combate, colocación libre, propietario director y límite16. No acepta totales del cliente. Procedencia por huella de plantilla; ampliar el catálogo no invalida entradas anteriores. La copia verifica la plantilla y conserva propietario/controlador de PNJ; solo reasigna PJ. PG actuales/posición son estado dinámico validado. Modificar estadísticas mediante el editor avanzado marca explícitamente corrección excepcional, sin transferir el PNJ al jugador.

La ficha muestra cobertura y fuentes; el invitado consulta sin guardar. El contexto del director conserva estadísticas y omite auditoría repetida. /licenses/ sirve únicamente los tres avisos declarados; exportar campaña con PNJ incorpora sus textos una vez en la raíz de la copia. No añade escrituras de licencia al estado de Firebase ni tokens al modelo.

HTTP/Waitress, copia, permisos, deduplicación, alteraciones de ficha y licencia pública/exportada correctos; navegador anfitrión/invitado/móvil correcto, cero acciones por consultar. Suite previa530 correcta sin omisiones (222,759s); final con ajuste de licencias en ejecución, .deps/npc-preparation-final-legal-tests.log. Todavía sin despliegue de este API, sin interfaz de incorporación y sin encuentro autónomo habilitado.

Validación final: **531 pruebas completas con emulador correctas sin omisiones (230,223s)**. Exportación contiene avisos una sola vez y la consulta pública de los textos no accede a Firebase. Navegador de preparación correcto; cambios pendientes de despliegue/verificación en este punto.

Estado: fábrica local aislada, sin API de incorporación, interfaz de PNJ ni encuentro autónomo nuevo. Prioridad: permitir un conflicto acotado del módulo actual sin que el anfitrión tenga que calcular o escribir estadísticas. No representa todavía una aventura completa ni un hito de prueba personal.

`catalogs/npc-catalog.json` contiene una primera plantilla de datos, identificada por sistema/versión/fuentes: goblin combatiente 1 del Bestiario aportado. `npc_catalog.prepare` devuelve una copia de los valores y un registro de procedencia con huella, fuentes, perfil, cobertura y límites. No convierte reglas entre sistemas, no sube niveles, no usa el creador de PJ como creador de criaturas y no realiza llamadas de IA, Firebase ni nuevas tiradas.

La entrada se contrastó visualmente en Bestiario Devir PFR002, depósito B 5055-2014, erratas 2.0: PDF 167/folio166. PG7 incluye el bonificador de clase predilecta; CA16, toque13, desprevenido14; espada corta+2/1d4, iniciativa+6 y30pies. Bestiario PDF7/folio6 explica que omitir espacio/alcance significa casilla y alcance de5pies; no se deduce del nombre de la criatura. Espada corta Pequeña y crítico19–20/×2 comprobados en Reglas básicas PDF143/folio142 y PDF185/folio184.

El perfil se limita a espada corta preparada y combate básico dentro de las condiciones del motor. No automatiza arco/munición, visión en oscuridad, cambio de armas, tesoro ni PX. Esas capacidades siguen declaradas, sin eliminarlas de la criatura ni atribuir la limitación al manual. Un futuro encuentro deberá acreditar condiciones y conservar decisiones del jugador; este preparador por sí solo no valida la escena.

Los datos reglamentarios identificados se acompañan de OGL1.0a y avisos de ambas fuentes en licenses/NPC-CONTENT.md. Las licencias originales se verificaron en Bestiario PDF328/folio327 y Reglas básicas PDF570/folio569. No se incorporan ilustraciones, ficción ni maquetación de los libros. Las capturas permanecen en .deps, fuera del repositorio.

Validación local: cuatro pruebas específicas, con PG publicados, fuentes, restricciones de sistema/modo, aislamiento de copias y crítico real del motor. Veinticinco pruebas junto al creador y combate correctas. No se ha realizado inferencia nueva ni se ha certificado un encuentro completo con proveedor real.

Siguiente integración: una incorporación atómica desde catálogo, identidad/controlador y procedencia verificables al recuperar, permisos y colocación válida sin editar estadísticas. Después, un encuentro de aventura preparado que se active mediante decisiones del jugador, con reglas e iluminación declaradas, y consecuencias/reanudación. Revisar privacidad del módulo heredado y no equiparar preparación por API con una aventura sin maestro humano.
