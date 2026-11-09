# Acciones concurrentes por campaña

9 de noviembre de 2026. El servidor serializaba todas las acciones con un único cerrojo: una respuesta lenta del director impedía confirmar acciones de otras campañas en el mismo proceso. La prueba HTTP nueva reproduce ese fallo antes del cambio.

`campaign_locks.CampaignLocks` mantiene un cerrojo reentrante por campaña. Cuenta titulares y solicitudes en espera; elimina la entrada cuando nadie la usa. El registro tiene una protección breve que nunca permanece adquirida durante llamadas a IA o Firebase. No conserva indefinidamente identificadores de partidas inactivas.

`server.execute_action` conserva dentro del cerrojo la comprobación de duplicados, carga, versión, preparación/captura, reglas y confirmación. No separa por jugador: dos participantes de una misma campaña siguen compartiendo orden. Las transacciones y el control de versión persistentes siguen siendo autoridad entre procesos. Esto no certifica exclusión de llamadas facturables entre varias réplicas ni capacidad de un grupo concreto.

Pruebas sin IA real: HTTP/Waitress y emulador Firestore con director detenido mediante eventos. Otra campaña crea su personaje antes de liberar la respuesta; una acción de la misma campaña espera y recibe409 si quedó desfasada; un duplicado espera y devuelve duplicate sin una segunda llamada ni mensaje de director. Dos pruebas unitarias adicionales comprueban reentrada, liberación tras excepción y limpieza. Las cinco pasan; 914 pruebas completas correctas454,616s en `.deps/campaign-concurrency-final-tests.log`.

No añade llamadas, tokens, lecturas ni escrituras. Permite aprovechar los hilos existentes; si todos están ocupados siguen existiendo límites del servidor. La prueba de dos campañas independientes no equivale a certificar multijugador ni rendimiento bajo carga.

Navegadores locales correctos: memoria compartida con secretos/invitado y captura de respuesta perdida conservan el comportamiento anterior. `test_group_conflict_browser.cjs` añade un recorrido íntegro de dos perfiles nuevos, modo online y creador legal para ambos: selección de hablante limitada al propietario, nota privada aislada, versión desfasada409 sin perder el texto ni reenviar automáticamente, revisión y segundo envío explícito con nueva versión, un solo mensaje confirmado para ambos tras recarga, teclado y móvil. Retrasa únicamente la consulta periódica del invitado para reproducir la versión antigua; la actualización tras409 sí llega del servidor real local. Cero inferencias, sin editar estado ni sustituir respuestas de acciones. El primer intento del guion omitía el objetivo obligatorio de creación y se corrigió el guion; no se cambió la aplicación.

Suite completa terminada, sesión74944:914correctas454,616s. Sin cambios de comportamiento posteriores al arranque; solo documentación, docstring de serve y un navegador adicional. Listo para publicar y verificar en lectura.
