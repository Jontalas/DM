# Premisa obligatoria: mínimo coste de uso

El uso de IA, base de datos y almacenamiento remoto debe ser el mínimo imprescindible en todo momento para ahorrar la mayor cantidad posible de dinero pagado por el uso de la aplicación. Esta premisa se aplica a toda función nueva, corrección y decisión de arquitectura.

- Resolver mediante código determinista, cálculo local o intervención del jugador todo lo que no requiera IA. Llamar al modelo solo cuando aporte una respuesta necesaria para la partida; evitar llamadas automáticas por navegación, sincronización o acciones administrativas.
- Reducir las llamadas y los tokens: enviar únicamente el contexto pertinente, limitar la salida y reutilizar resultados cuando sean válidos y respeten los permisos. Evitar duplicados y reintentos facturables innecesarios.
- Minimizar lecturas, escrituras, consultas y transferencias de Firebase. Evitar consultas periódicas sin necesidad, escrituras sin cambios y volver a cargar o indexar recursos que no han cambiado. Priorizar caché, consultas acotadas, agrupación de cambios y sincronización adaptativa cuando sean compatibles con la consistencia requerida.
- Conservar solo los datos e índices necesarios. Definir una política de retención y limpieza para datos temporales u obsoletos; proteger partidas, originales y copias necesarias antes de eliminar cualquier dato.
- Elegir la alternativa viable de menor coste total de alojamiento, IA, operaciones y transferencia. Explicar cualquier gasto recurrente nuevo y su necesidad; no activar servicios de pago adicionales sin autorización.
- Evaluar el coste por acción y con varios jugadores antes de implementar funciones. Documentar las llamadas y operaciones evitadas y las limitaciones pendientes; no presentar esta política como una optimización ya implementada.
- El ahorro debe preservar la seguridad, privacidad, persistencia, reglas del juego y coherencia entre jugadores. No reutilizar datos privados entre usuarios ni omitir validaciones para reducir operaciones.
