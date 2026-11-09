# Siguiente bloque: dos participantes y recuperación de conflictos

9 de noviembre de 2026. El aislamiento entre campañas de CONCURRENCIA_CAMPANAS.md no certifica una campaña compartida. El siguiente recorrido debe usar dos sesiones reales de navegador de una campaña técnica, con personajes creados legalmente por sus propietarios, respuestas simuladas y emulador. No usar invitación opcional ni ensayos reales cerrados.

Primer avance comprobado: `test_group_conflict_browser.cjs`, dos perfiles/fichas propios desde GUI, servidor local con TestStore y sin proveedor. Nota privada aislada, hablantes propios,409 conserva texto, reenvío explícito y confirmación única compartida, recarga/teclado/móvil correctos. No usa emulador ni espera a IA: esa parte sigue pendiente para el recorrido conjunto; los tres HTTP de CONCURRENCIA_CAMPANAS.md sí usan emulador y espera simulada, todavía con una identidad por campaña.

Contrato a comprobar antes de ampliar capítulos a grupos:

- Mientras una declaración espera al director, otro participante conserva su texto y puede consultar lo ya cargado. No puede decidir por el personaje ajeno ni recibir secretos del anfitrión.
- Una acción concurrente con versión antigua no confirma cambios ni genera una segunda inferencia. Se explica que la partida cambió y se conserva la decisión pendiente para revisión del propietario; no reenviar automáticamente con otro identificador una petición facturable.
- Tras recibir la actualización, el propietario revisa y vuelve a decidir. La acción confirmada aparece igual para ambos; recarga y reanudación no la repiten. Notas privadas siguen siendo privadas.
- Una respuesta capturada pero no confirmada se recupera con su identidad/cuerpo originales. Un tercero no puede aprovechar esa captura. Las operaciones deterministas siguen sin IA.

Reutilizar los mecanismos existentes de versión, captura, borrador y propiedad. Primero localizar el primer fallo reproducible con transporte HTTP y después comprobar la interfaz desde perfil nuevo, teclado y móvil. No añadir sondeos, escrituras ni IA por consultar ayuda o cambiar de herramienta.

La siguiente ampliación de capítulos colectivos requiere además una decisión de objetivo que preserve la agencia de todos, reglas explícitas para personajes presentes y pruebas de privacidad/continuidad. No quitar la restricción individual actual solo para hacer pasar un recorrido. Dos participantes y una investigación tranquila no autorizan anunciar tamaño de grupo general ni combate multijugador completo.

Riesgo pendiente identificado al leer `FirestoreStore.join`: incorporarse incrementa la versión de campaña y la ruta de invitación no pasa por execute_action. Hay que reproducir una incorporación mientras se espera una respuesta del director: podría invalidar la confirmación de una respuesta ya pagada. Existía con el mutex global anterior; los cerrojos de acciones por campaña no lo resuelven por sí solos. No afirmar todavía un fallo observado en navegador ni cambiar versiones/capturas sin prueba. Preparar HTTP con eventos y emulador, exigir una sola inferencia y preservar la entrada/respuesta original ante cualquier recuperación. Si se necesita una lectura adicional exclusivamente al incorporarse para coordinar el acceso, justificarla frente a separar versiones de miembros/estado; no introducir consultas periódicas.
