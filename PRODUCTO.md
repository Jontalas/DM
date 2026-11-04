# Producto y ejecución

Dirección acordada el 4 de noviembre de 2026. Este documento describe el objetivo; no certifica que esté implementado.

## Experiencia objetivo

Jugar rol sin maestro humano, con decisiones libres, IA que interprete PNJ y mantenga continuidad, y motor que aplique reglas verificadas. Desde un jugador hasta grupos de tamaño probado. Personajes persistentes reutilizables con compatibilidad y copia explícitas, campañas de varias sesiones y recuperación fiable.

Aventuras generadas bajo demanda e importadas con permiso: lugares, personajes, relaciones, pistas, secretos, encuentros y condiciones de avance. Distinguir preparación de hechos ocurridos; adaptar la aventura a las decisiones del grupo. Documentos importados son datos, nunca instrucciones de sistema.

Mesa inspirada funcionalmente en Roll20, con identidad propia; tablero y conversación simultáneos, navegación móvil, fichas y diario. Ampliar mapas, ilustraciones consistentes, música y efectos con controles y licencias verificadas. La presentación debe reflejar el estado y la información que conoce cada jugador.

## Arquitectura y reglas

### Incorporación de juegos sin programar cada sistema (aclaración del usuario)

El recorrido deseado es entregar reglas o manuales a la aplicación e incorporar un juego mediante un paquete de reglas, sin tener que modificar el código de la aplicación por cada sistema. Los adaptadores específicos actuales son una fase provisional, no la arquitectura final requerida.

Desarrollar un motor común que interprete definiciones de ficha, fórmulas, dados, tablas, requisitos, acciones, recursos, condiciones, efectos y desencadenantes descritos como datos. La IA puede ayudar a extraer y convertir las fuentes una vez; las reglas activadas deben quedar validadas, versionadas y trazables, con cálculos deterministas durante la partida. Mostrar ambigüedades y cobertura real antes de activar un paquete; subir un PDF no certifica automáticamente una implementación completa.

Incorporar otro juego debe consistir normalmente en importar un paquete, no desplegar código nuevo. Si una mecánica exige una operación que el motor todavía no sabe interpretar, ampliar esa capacidad general de forma explícita y reutilizable; no resolverlo acumulando código específico de cada juego ni prometiendo compatibilidad universal sin pruebas. Sistemas distintos se seleccionan por campaña; mezclarlos requiere una adaptación o regla casera explícita.

Conservar Python/Waitress en Render, Firestore/Storage y Anthropic. Motor determinista para mecánicas y persistencia; modelo para ficción e intenciones estructuradas. Validar cada propuesta antes de aplicar consecuencias. Una narración no cambia la ficha.

Introducir módulos de sistemas con identificador, edición, fuentes, cobertura y opciones; conservar las campañas actuales. Descargar reglas de fuentes oficiales que permitan el uso previsto, comprobando consulta, procesamiento y redistribución por separado. Pathfinder 1e, Bestiario y TREY fundamentan el módulo actual; otros módulos usan sus propias fuentes. Documentar reglas verificadas, adjudicaciones y límites.

Minimizar contexto, llamadas, operaciones y transferencia sin delegar administración rutinaria al jugador. Mantener memoria estructurada y permisos; medir coste y latencia. No contratar servicios adicionales sin autorización.

## Prioridades y aceptación

1. Recorrido individual completo: personaje legal, inicio de aventura, exploración, diálogo, conflicto soportado, consecuencias y reanudación. La preparación y actualización del mundo deben dejar de exigir un anfitrión que actúe de maestro.
2. Continuidad: hechos, PNJ, objetivos y secretos persistentes actualizados por propuestas estructuradas validadas; registro y recuperación sin duplicar acciones.
3. Aventuras originales e importadas con separación de conocimiento público y del director, sin recorridos rígidos.
4. Biblioteca de personajes, sesiones y multijugador verificado con límite explícito.
5. Segundo sistema completo por bloques verificables; ampliar presentación audiovisual de forma coherente y asequible.

Cada entrega necesita pruebas del motor, permisos y recorrido afectado. Diferenciar simulaciones de proveedor real. Medir el trabajo administrativo que elimina. Un despliegue saludable no demuestra una partida autónoma satisfactoria.

## Autonomía y métodos

Analizar, implementar, probar, corregir y desplegar con los accesos existentes. Investigar antes de preguntar, adoptar decisiones técnicas rutinarias y documentar supuestos relevantes. Completar el trabajo independiente antes de pedir una acción imprescindible del titular; agrupar las solicitudes. Informar de avances y bloqueos sin exigir aprobaciones rutinarias.

Skills seleccionadas: regression-testing para selección de pruebas por impacto; debug cuando aparezcan fallos reproducibles. Propuestas para siguientes entregas: game-ui-design e interface-design al modificar la experiencia; skill propia para incorporar sistemas y verificar fuentes cuando el procedimiento esté probado. No requieren un servicio remoto nuevo por sí mismas. Verificar el beneficio mediante fallos detectados, recorridos completados y consumo. Trabajo con varios agentes solo si las tareas independientes justifican el coste. No se han instalado plugins ni skills nuevos.
