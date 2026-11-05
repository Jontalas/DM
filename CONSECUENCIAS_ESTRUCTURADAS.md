# Consecuencias verificables de aventura

Contrato en diseño, no disponible todavía. Continúa el trabajo de RESOLUCIONES_NARRATIVAS.md. No introduce reglas de Pathfinder ni certifica una aventura completa.

Integración local posterior: `prepare_pack_discoveries` prepara una sola vez un catálogo privado inmutable, únicamente para el anfitrión, con permiso provided-adventure, fuente original existente y objetivos abiertos conocidos. Requiere action-results. Es una API técnica de preparación; todavía no hay conversión automática desde una aventura ni asistente de preparación. No se presenta como recorrido autónomo terminado.

El motor vincula automáticamente todos los descubrimientos pertinentes al objectiveCheck antes de tirar. Revelación y evidencia se confirman con la acción; fracaso, retirada o vínculo vacío no revelan. El diario muestra únicamente recibos confirmados. La copia comprueba fuente exacta, cronología, registro/evidencia y valores, sin tirar ni inferir. Con fuente separada en almacenamiento, vista y resolución usan los datos ya cargados: no vuelven a leer el original. La preparación sí lo recupera una vez para contrastar citas. Contrato optativo discoveries-3 solo cuando existe catálogo; campañas/capturas anteriores conservan contexto anterior.

Las citas son exactas, pero la pertinencia semántica entre descubrimiento y objetivo sigue siendo una decisión de preparación aportada, no una interpretación certificada del manual o de la fuente. No hay premios ni efectos reglamentarios adicionales. Navegador con proveedor simulado comprobado: secreto oculto antes, pérdida de respuesta al resolver, revelación única, consulta local, persistencia, invitado y móvil. Pruebas HTTP y Waitress de preparación/permisos, resolución sin lectura del original, duplicados y copia correctas. Suite completa: 433 pruebas con emulador sin omisiones, correctas (166,474 s). Corregida conservación del texto original CRLF al cargar archivo en el editor; exportación exacta comprobada en navegador. Despliegue/verificación de producción pendientes.

## Problema que debe resolver

Un éxito calculado puede cerrar un objetivo vinculado, pero el descubrimiento concreto sigue dependiendo de prosa. La fuente privada no es por sí sola un catálogo ejecutable: citarla no autoriza al servidor a inferir desplazamientos, daño o decisiones de personajes.

## Primer bloque acotado

Representar descubrimientos como hechos inmutables de aventura, con identidad, texto público, procedencia y visibilidad. Una definición preparada debe indicar el objetivo al que pertenece y el resultado booleano requerido. La solicitud concreta fija esa identidad antes de tirar. Solo su resolución confirmada puede revelar el hecho; no un éxito anterior ni otra exploración del mismo tipo.

El primer bloque solo revela información. No concede equipo, experiencia, desplazamiento, control de PNJ ni efectos sobre otras fichas. Esas capacidades requieren contratos y reglas independientes. La preparación de consecuencias debe ser revisable y validada; una invención del director no se convierte en una consecuencia reglamentaria.

## Invariantes para implementar

- Identidades y definiciones estables; modificar una definición requiere una nueva identidad.
- Límite explícito de registros, bytes y revelaciones por resolución.
- Hechos privados ausentes de la proyección pública hasta su revelación.
- Vínculo guardado en la solicitud antes de confirmar dados y opciones.
- Revelación, evidencia y cambio de ficha en una sola confirmación consistente.
- Reintento idéntico conserva el hecho y los dados; no genera otra inferencia.
- Copia reproduce evidencia, orden, propietarios y visibilidad sin tirar ni consultar al modelo.
- Resultado canónico y contexto de continuación incluyen solo hechos realmente revelados.
- Consulta del diario local sin IA, escrituras ni cargas adicionales.
- Campañas y capturas anteriores conservan sus contratos; ampliación optativa y versionada.

## Casos de aceptación

Éxito vinculado revela una vez; fracaso no revela; éxito anterior no cuenta; acción ajena no revela; vínculo cambiado después de solicitar se rechaza; opciones distintas no producen evidencia válida; invitado no recibe secretos; copia rechaza pruebas manipuladas. Comprobar también confirmación interrumpida y recuperación con cliente nuevo.

Antes de integrar este bloque, decidir su procedencia: paquete de aventura verificable y autorizado o adjudicación excepcional explícita. No presentar generación libre como verificación de una fuente. Ninguno de estos pasos requiere intervención del usuario mientras se trabaja con ejemplos propios y pruebas técnicas.
