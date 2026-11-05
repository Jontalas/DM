# Consecuencias verificables de aventura

Contrato en diseño, no disponible todavía. Continúa el trabajo de RESOLUCIONES_NARRATIVAS.md. No introduce reglas de Pathfinder ni certifica una aventura completa.

Primer núcleo implementado de forma aislada en adventure_discoveries.py: preparación por cita exacta y huella de fuente, vínculo a solicitud/objetivo/campo, recibo de éxito y proyección sin secretos. Tres pruebas cubren Unicode/CRLF, alteraciones, referencias, fracaso, solicitud ajena, duplicados y privacidad. Nueve pruebas correctas junto con resultados canónicos. Aún no se habilita en campañas ni se ofrece como función disponible. Siguiente integración: guardar catálogo privado inmutable, ligar antes de tirar, confirmar recibos junto a la acción y reproducirlos al importar; después contexto y diario. La automatización de preparación no debe convertirse en administración rutinaria del jugador.

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
