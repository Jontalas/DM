# Sencillez y orientación

Directiva permanente del usuario del6 de noviembre de2026, incorporada a AGENTS.md y PRODUCTO.md. Es un requisito transversal del producto; no una declaración de que la interfaz actual ya lo cumple.

Cada pantalla debe responder, con pocas palabras: qué está pasando, qué puedo decidir ahora y cómo continúo. Mostrar las opciones pertinentes al momento y al permiso del jugador. Explicaciones extensas, comprobaciones reglamentarias y herramientas avanzadas quedan disponibles mediante despliegue progresivo. Las ayudas funcionan con teclado y tacto, sin depender solo de hover. Nunca ocultar una consecuencia necesaria para decidir.

## Aplicación inmediata

Recuperación automática nueva: la pantalla lidera con el estado presente (consciente/incapacitado o muerto) y cómo continuar. La instantánea anterior no se anuncia como situación actual. Comprobaciones horarias agrupadas en un resumen con todas las tiradas bajo detalles; abrirlo con teclado no envía acciones. La muerte desactiva las tiradas de ficha y oculta solicitudes imposibles; la ficha se llama «Tu personaje», sin anunciar que está listo para jugar. Si no hay director disponible, la casilla de IA queda desactivada y se explica lo que sí puede hacerse, sin pedir configuración técnica al jugador. Navegadores verifican recuperación y muerte, copia por interfaz, recarga y móvil; pruebas de ficha y aventura mantienen sus recorridos.

Primer bloque integrado y verificado localmente: situación y decisiones principales del encuentro visibles; límites bajo «Qué incluye este encuentro» y reglas de auxilio bajo «Cómo funciona el auxilio». Se mantienen visibles el riesgo de muerte al esperar y el coste de auxilio a0PG. Se explica cómo continuar si falta turno, acción o cercanía. Dados rápidos del compositor bajo «Tirar un dado», con aviso de tirada libre sin modificadores. Los resúmenes tienen foco visible y se abren con teclado y tacto.

Evidencia: navegador del encuentro comprueba ayudas cerradas al entrar, apertura/cierre mediante Enter y tacto sin enviar acciones, auxilio y móvil sin desbordamiento. Navegador general mantiene dados rápidos, dos jugadores y tablero/chat en escritorio/móvil. Navegadores de aventura Pathfinder y plan-3 correctos después del cambio del compositor. Proveedor simulado; ninguna inferencia real nueva. Esta evidencia cubre estos recorridos, no la revisión completa pendiente.

Revisar el encuentro preparado para mostrar primero situación y decisión; separar los límites extensos en una ayuda desplegable. Mantener visibles el riesgo de esperar sin auxilio y el coste de actuar a0PG. Simplificar las instrucciones de auxilio y explicar turno, cercanía y acción disponible. Probar que abrir ayuda no envía acciones ni llama a IA, y que funciona en móvil.

## Revisión pendiente del resto de la aplicación

Tercer bloque local: mesa con instrucción breve según turno, selección y acciones gastadas; el aviso solo se actualiza cuando cambia. Ataque visible durante combate, con causa concreta si falta perfil, turno, acción o cercanía. Selección de objetivo actualiza la ayuda localmente. Inicio de iniciativa se oculta durante combate y durante la decisión inicial del encuentro preparado; los botones de recorrido aparecen al trazarlo. Correcciones, finalización manual y opción de adversarios bajo la sección de excepciones; avisos de pausa y reintento conservados. No se cambian reglas ni permisos.

Evidencia: encuentro desde creador añade movimiento real fuera de combate, ataque desactivado por distancia, acercamiento mediante recorrido confirmado y ataque habilitado sin cálculos manuales. Después completa auxilio y copia/recarga. Navegadores de mesa de dos jugadores, gestos/permisos/móvil y creador pasan; navegación/medición siguen sin escrituras. Es una adaptación propia a la directiva de claridad, no una equivalencia observada de Roll20.

Segundo bloque local: bienvenida con elecciones básicas, ejemplo de premisa y personalización opcional plegada; límites de contenido accesibles y aviso de cobertura pendiente. Ritmo de TREY explicado como umbral, sin prometer duración temporal. Invitación plegada al inicio y abierta automáticamente al recibir enlace; tras entrar se retira ese parámetro de la URL para que recargar recupere la partida. Estado técnico del servidor bajo demanda. Se preservan opciones/valores y selección de sistema.

La biblioteca vacía queda plegada y una biblioteca con partidas se abre automáticamente. Se conserva el acceso a importar credenciales bajo su sección. Captura móvil revisada sin desbordamiento, con menos contenido previo al formulario y sin la tarjeta técnica vacía inicial. La prueba de biblioteca verifica también restauración desde archivo y el despliegue de partidas existentes.

Verificación: la prueba de dos jugadores reproduce el enlace de invitación y recarga; detectó y permitió corregir el retorno indebido a bienvenida. Comprueba valores de personalización después de cerrar detalles y ayudas con teclado sin POST. Navegadores de biblioteca, paquete de reglas, Cairn experimental y encuentro pasan con la bienvenida nueva; no son evidencia de soporte completo de esos juegos.

- Bienvenida y entrada: una ruta clara a personaje y partida; evitar opciones técnicas prematuras.
- Mesa: tablero y conversación accesibles, con herramientas pertinentes al turno y ayuda breve.
- Ficha y creador: elecciones legales guiadas; cálculos explicables bajo demanda.
- Diario: lectura de lo ocurrido como recorrido principal; separar preparación y correcciones avanzadas.
- Reglamentos y dados: consulta y ayuda accesibles sin exigir comprender contratos, formatos o administración del motor.
- Errores y recuperación: explicar qué ocurrió y el siguiente paso, conservando la acción pendiente cuando proceda.

La aceptación exige comprobar recorridos nuevos, teclado y móvil: decisiones relevantes visibles, ayuda fácil de encontrar, sin pérdida de agencia ni promesas de funciones pendientes. Documentar evidencia por recorrido; no considerar que una ayuda añadida certifica toda la usabilidad.
