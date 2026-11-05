# Resoluciones entre fichas: kernel y siguiente integración

Capacidad local `target-sheets`, todavía sin ruta de campaña. No es combate disponible ni una implementación de Pathfinder. El ejemplo propio CC0 usa dos recursos abstractos; sus números no se atribuyen a un manual.

Validación del kernel: 458 pruebas completas con emulador correctas sin omisiones (176,761 s), incluidas cinco pruebas nuevas de dos fichas/condiciones/origen simultáneo/ciclos/aislamiento. Navegador normal con acción de objetivo oculta correcto; captura original antigua revalidada sin red ni inferencia. Desarrollo en feature; no desplegar como ataque utilizable hasta terminar la siguiente integración y su proyección privada/pública.

## Contrato matemático implementado

Una acción declara `target:true`. Sus expresiones pueden consultar `target.campo` mediante el formato normal de referencias; los efectos usan `scope:target` para escribir en la otra ficha y `scope:self` (u omisión) para escribir en quien actúa. Un campo se puede asignar una vez por ámbito. Las etapas de creación no admiten objetivos externos. Las dos fichas tienen que pertenecer al mismo contenido exacto de paquete y haber completado su perfil.

`preview_targeted` valida requisitos y dados sin tirar. `execute_targeted` calcula una sola secuencia de dados y devuelve las dos fichas más la traza completa. Todos los efectos iniciales leen las dos instantáneas originales; el orden de aplicación no convierte un efecto en entrada implícita del siguiente. Después se resuelven por separado los desencadenantes de cada ficha hasta estabilidad, bajo presupuesto y detección de ciclos. Una excepción no modifica ninguna de las fichas originales. Cada resolución incrementa las dos revisiones, aunque un fallo no cambie campos del objetivo; revisión no significa daño ni paso de tiempo.

La traza de quien actúa mantiene sus cambios, dados, fuentes, desencadenantes y salidas declaradas; `trace.target` contiene revisión anterior/posterior y cambios/desencadenantes del otro lado. Es evidencia privada de resolución: no debe enviarse íntegra al cliente. El kernel no decide propietarios, identidad física, selección, ubicación, visibilidad, alcance, turnos ni adjudicaciones del juego. Lo que puede resolverse depende de las fórmulas y cobertura verificadas del paquete.

La ruta individual rechaza acciones con objetivo antes de tirar. Director, preparación de objetivos e interfaz no las ofrecen hasta que exista el recorrido conectado. Los paquetes anteriores conservan los mismos contratos y trazas. El cierre de un objetivo de aventura solo puede usar un resultado booleano propio de la acción, no un efecto de igual nombre sobre otra ficha.

## Siguiente integración, aún pendiente

1. Unir actor_references con la solicitud concreta: ids de actor/PNJ, paquete, decisiones y ambas revisiones antes de obtener dados. No confundir PNJ conocido con objetivo presente o alcanzable. Declarar los requisitos de escena y reglas realmente soportados, rechazar lo demás antes de IA/dados.
2. Registrar cuándo se preparó un actor respecto al registro mecánico. Las acciones futuras no pueden apuntar a un actor que aún no existía. La preparación privada no debe anunciar nombres ni existencia de PNJ ocultos en mensajes públicos.
3. Conservar evidencia de resolución completa en un registro privado ligado al evento público. Reproducir la cronología de las fichas de jugadores y actores desde sus creaciones, incluidas ambas revisiones y dados. El validador actual de actores solo admite su ficha inicial preparada; debe ampliarse antes de guardar una ficha modificada por otra acción. No saltarse esa validación.
4. Confirmar fichas, prueba privada, mensaje público y barrera de acción en el mismo lote. Usar la semilla duradera ya existente para toda la resolución y probar fallo de commit/cliente nuevo/concurrencia.
5. Publicar únicamente el resultado permitido: el registro privado puede contener campos o modificadores ocultos. Examinar también si cantidad, caras o condición de una tirada dependen de un campo privado del objetivo; no filtrar valores mediante su forma. Hasta disponer de una política de visibilidad, limitar los casos ofrecidos explícitamente.
6. Conectar resultados canónicos y continuación con un contrato nuevo optativo. Copiar, recuperar o consultar no requiere inferencia. Probar el motor antes de una escena real de presupuesto cerrado; no repetir sesiones fallidas para buscar una aceptación favorable.

No introducir valores de CA, daño, alcance, iniciativa o clases del módulo Pathfinder en el kernel. Antes de construir su paquete de conflicto, verificar cada regla pertinente contra Reglas básicas/Bestiario y las excepciones; PNJ_FUENTES.md solo documenta una primera consulta del creador. La selección local y los cálculos se resuelven sin operaciones remotas adicionales.
