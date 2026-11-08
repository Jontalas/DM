# Comprobación integrada del patio y el envío

## Combate, recuperación e investigación con proveedor real

El8 de noviembre de2026 se verificó otra campaña técnica desde perfil nuevo mediante GUI, en36f393e2b60041f1d26996ee1727399c3f356102/encuentro1.13. Creador humano guerrero1 por defecto, sin editar estadísticas, elegir idiomas, dados físicos ni acciones por API. Dos ataques y los turnos reales del servidor dejaron al PJ con12PG y a la guardiana herida. El jugador eligió esperar su estabilización; después eligió la espera preparada. Dos comprobaciones horarias sin ayuda dejaron a la guardiana consciente con−2PG. No se inventaron curación ni asistencia.

Una sola petición real a Haiku,6183ms de cliente, interpretó «Empiezo a investigar el patio y buscar las pistas del peaje» mediante la decisión validada. La narración fue revisada visualmente: guardiana sentada/despierta/herida y elección de qué revisar en manos del PJ; no concede pistas ni curación. No se midieron tokens o precio. El resto fueron controles deterministas:5pistas/3escenas/regreso, copia desde diario, importación y recarga, teclado/móvil. El resultado final conserva PJ12/guardiana−2, cuidados, prueba de consciencia y único mensaje del director.

Un lector posterior comprobó revisión/salud exactas, fichas, pruebas,5pistas/3transiciones y objetivo; cero POST/inferencias. Otro comprobó «Salir», cierre del contexto del navegador conservando su perfil local, nueva apertura y «Volver a esta partida» desde biblioteca con teclado: misma campaña/versión, PG/pruebas/objetivo y respuesta única intactos, cero POST/IA.

Sesión protegida `.deps/combat-investigation-live-session.json`: no imprimir, subir, borrar o renombrar. **No repetir** `verify_combat_investigation_live.cjs`. Lectores `verify_combat_investigation_production_browser.cjs` y `verify_combat_resume_production_browser.cjs` solo en lectura. El ensayo se preparó contra un servidor local simulado; se corrigió un selector del guion para escritorio, donde el tablero está siempre visible y su pestaña se oculta. No fue un fallo del juego y no hubo inferencia real durante ese ajuste.

Esto añade el recorrido de combate y vuelta frente al acuerdo anterior. El diálogo libre real con el PNJ se comprobó después por separado: recorrido técnico correcto, pero el modelo inventó una condición para consultar papeles ya autorizados. Fallo semántico y corrección en COHERENCIA_PNJ_PREPARADOS.md; hito1 pendiente, no sustituir esa evidencia por una oferta prefijada ni por número de pruebas. Calendario general, recursos diarios, libertad de campaña, opciones no verificadas y multijugador certificado siguen pendientes.

## Acuerdo e investigación declarada anteriores

El8 de noviembre de2026 se verificó en producción3e6f4efc247288bbb77d3183afb08efcdc123c19 un recorrido nuevo, desde un navegador sin sesión, mediante los controles de la aplicación: crear campaña técnica, crear humano guerrero1 con valores legales por defecto, entrar en encuentro1.10 y elegir acuerdo. Sin preparar estadísticas a mano ni cambiar idiomas.

Una declaración de acción, «Empiezo a investigar el patio y buscar las pistas del peaje», fue interpretada por el director real y activó la investigación mediante la decisión preparada validada por el servidor. Se registró una sola respuesta de IA,8199ms de cliente. Se revisó su narración: sitúa la búsqueda sin conceder hallazgos ni escoger el siguiente objeto por el PJ. No se expusieron contadores reales de tokens/precio; no se estima un ahorro económico medido.

El resto utilizó controles deterministas: dos pistas en el patio, una en el cobertizo y dos en el almacén, con dos viajes explícitos. El objetivo global se completó; PJ16PG/guardiana6PG, guardiana en patio. Copia desde el diario, importación y recarga conservaron fichas, pistas, objetivo y única respuesta. Teclado y móvil sin desbordamiento. Los lectores posteriores verifican estas mismas campañas sin POST ni nuevas inferencias.

El primer guion tenía una aserción incorrecta: esperaba completar el objetivo al llegar al cobertizo. La aplicación conservó correctamente las pistas pendientes. Se corrigió la verificación continuando la misma campaña hasta la recepción del almacén, sin repetir la llamada de IA ni crear otra campaña. No fue una corrección del juego.

Los checkpoints y exportaciones privadas están en `.deps/declared-investigation-live-session.json`: contiene credenciales, no imprimir ni incorporar a Git. Ensayo cerrado: **no repetir** `verify_declared_investigation_live.cjs` ni `finish_declared_investigation_verification.cjs`, ni borrar/renombrar la sesión. El lector `verify_declared_investigation_production_browser.cjs` admite EXPECTED_RELEASE y no ejecuta acciones.

Esta comprobación añade evidencia de decisión preparada real a los contratos y simulaciones anteriores. No incluye un combate real nuevo, noches declaradas al modelo, campaña abierta ni varios jugadores certificados. Los cuatro hitos de PRODUCTO.md siguen pendientes; no se solicita una prueba personal por este bloque.
