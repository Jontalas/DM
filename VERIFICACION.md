# Verificación de despliegue — 19 de octubre de 2026

Resultado: base técnica comprobada para Render + Firestore + Storage + Claude Haiku. El funcionamiento completo en producción todavía necesita la URL desplegada y una prueba real del director. Esta revisión no certifica que estén completadas todas las funciones del juego descritas en la petición original.

## Comprobado

- Dependencias instaladas sin conflictos (`pip check`). Desarrollo local en Python 3.14; Render está configurado para Python 3.13. No se ha ejecutado aquí ese runtime de Render.
- 53 pruebas Python correctas con el emulador oficial de Firestore, incluidas las rutas HTTP bajo Waitress, permisos, persistencia, deduplicación, concurrencia y lotes de manuales. Una primera ejecución encontró agotamiento de reintentos de una transacción concurrente en el emulador; la prueba aislada y la repetición completa pasaron. Conviene vigilar contención y errores transitorios en producción.
- JavaScript válido y prueba de sincronización correcta (`node --check static/app.js`; `node test_sync.cjs`).
- Acceso real de solo lectura al proyecto `dm-cronicas` y al bucket `dm-cronicas.firebasestorage.app`, mediante la cuenta configurada localmente. Metadatos de los tres PDF presentes; índices activos con 102 páginas de TREY, 577 de reglas y 329 de bestiario. Se leyó una página de muestra por índice; no se releyeron todas ni se descargaron los PDF completos para evitar gasto.
- Blueprint con Waitress, puerto de Render, una instancia y `/healthz`. Sin disco ni base de datos de Render; persistencia en Firebase. El plan configurado sigue siendo de pago (`0.5c-512mb`); no se ha contratado ni cambiado el plan.
- Modelo `claude-haiku-5-5` contrastado con la [documentación oficial de Anthropic](https://platform.claude.com/docs/en/models/overview). Solicitud y tratamiento de errores cubiertos con respuestas simuladas; no prueban acceso de una cuenta real.

## Ahorro aplicado y límites pendientes

- Consulta de sincronización cada 15 segundos en lugar de 2,5: seis veces menos solicitudes periódicas por pestaña visible. Se pausa en pestañas ocultas, se actualiza al volver y evita consultas periódicas solapadas. Las acciones propias siguen actualizándose inmediatamente; los cambios de otros jugadores pueden tardar hasta 15 segundos. No equivale a una reducción del 83 % de la factura total.
- Las comprobaciones de salud comparten un resultado correcto durante 60 segundos por proceso. Esto reduce lecturas, con hasta 60 segundos de demora para detectar una caída de Firebase.
- No se realizó ninguna inferencia facturable, escritura de prueba ni carga de manuales en el proyecto real durante esta revisión. Las lecturas reales fueron acotadas.
- Los PDF pesan aproximadamente 211 MB (TREY), 94 MB (reglas) y 72 MB (bestiario). Actualmente se sirven completos a través del servidor, sin soporte HTTP Range ni caché persistente del navegador: abrirlos repetidamente puede generar transferencia considerable. Conviene optimizar este recorrido antes de un uso intensivo del visor.
- Cada turno con IA aún envía el estado público, hasta 30 mensajes y hasta cinco fragmentos de manuales. Las campañas largas pueden aumentar el contexto. Quedan pendientes una selección más estricta del contexto y presupuestos configurables de entrada/salida.
- Siguen existiendo lecturas periódicas, consultas a manuales y escrituras de instantáneas. La limpieza administrativa es manual; los índices anteriores se conservan al reimportar. El coste no es todavía el mínimo posible.

## Pendiente para completar la puesta en marcha

1. Terminar la creación del servicio en Render y confirmar el plan elegido. Configurar allí `FIREBASE_PROJECT_ID=dm-cronicas`, `FIREBASE_STORAGE_BUCKET=dm-cronicas.firebasestorage.app`, `FIREBASE_SERVICE_ACCOUNT_JSON` y `ANTHROPIC_API_KEY` como secretos; no publicarlos ni enviarlos por chat. Las variables locales no se transfieren a Render.
2. Confirmar que el despliegue de la última revisión llega a Live. Verificar en su URL HTTPS `/healthz` y `/api/status`: libros con los recuentos anteriores, proveedor Anthropic y modelo Haiku. `aiConfigured` solo indica que existe una clave, no que funcione.
3. Crear una campaña, entrar con una invitación desde otro navegador, guardar una acción, recargar y comprobar continuidad y permisos. No poner credenciales de sesión en informes públicos.
4. Enviar una única intervención breve con «Responder con IA» para comprobar acceso, crédito y respuesta real de Claude. Esa acción consume API; revisar el uso en Anthropic. Una suscripción de chat no demuestra crédito de API.
5. Revisar presupuestos y consumo de Firebase, Anthropic y Render. Los avisos de presupuesto no deben confundirse con un bloqueo automático de gasto.

Sin una URL de Render y esa prueba real de Claude no se puede afirmar que todo esté listo para jugar en producción.
