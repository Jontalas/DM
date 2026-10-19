# Creación automática: primer recorrido jugable

«Crear personaje» abre un asistente con cuatro pasos: concepto, características, elecciones y equipo/resumen. También aparece «Crear mi personaje» en la conversación cuando el jugador no controla ninguna ficha. La edición manual queda dentro de opciones avanzadas. La referencia funcional es el [Charactermancer y la hoja Pathfinder de Roll20](https://help.roll20.net/hc/en-us/articles/360037773733-Pathfinder-by-Roll20); se consultó su documentación, sin instrumentar una partida de Roll20 ni afirmar equivalencia completa.

## Qué puede crearse

Humanos guerreros de nivel 1, adultos, Medianos, sin arquetipos, rasgos alternativos ni capacidades especiales. Hay tres puntos de partida modificables: guardián con espada/escudo, vanguardia con mandoble y centinela con hacha/escudo. Se puede conservar una propuesta y confirmar sin introducir ningún total manual, o cambiar sus elecciones:

- Compra de hasta 20 puntos, características base de 7 a 18 y +2 humano a una característica elegida. Es el presupuesto de este primer bloque, no un método impuesto por todas las campañas de Pathfinder.
- Tres dotes distintas del catálogo implementado, con al menos una de combate para el espacio adicional del guerrero. Soltura con el arma elegida e Iniciativa mejorada; Dureza, Gran fortaleza, Reflejos rápidos y Voluntad de hierro.
- Rangos de habilidad: mínimo de clase + Inteligencia, rango humano y, si se escoge, clase predilecta. Un rango por habilidad a nivel 1; +3 de clase solo si tiene rango. El catálogo incluye catorce habilidades, no todas las especializaciones posibles. Las que requieren entrenamiento no se preparan sin rango.
- Clase predilecta: +1 PG o +1 rango; idiomas adicionales por Inteligencia, con Común incluido.
- Espada larga, mandoble o hacha; cuatro armaduras y escudo de madera ligero/pesado o sin escudo. No se permite combinar mandoble con escudo. El arma seleccionada se considera empuñada, a una mano o dos según el catálogo.

Se calculan PG iniciales con dado máximo, Constitución, clase predilecta y Dureza; CA normal, desprevenido y toque; tres salvaciones; iniciativa; ataque base y Fuerza/Soltura; daño y críticos; habilidades y sus penalizadores. Se prepara el perfil que necesita el motor de combate, sin pedir al jugador que marque o complete sus campos.

El equipo parte de las 175 po medias del guerrero. Se descuentan arma, armadura, escudo y un equipo de viaje básico; el atuendo inicial es gratuito. Se cuentan el peso de todo el equipo y las monedas restantes, se determina carga y se aplica el peor límite de armadura o carga sin acumular ambos. Los penalizadores de armadura y escudo sí se suman entre ellos. La velocidad queda lista para el tablero. El inventario inicial no es aún un gestor de compras o consumibles durante la aventura.

Este primer bloque exige Fuerza final 10 o más porque el motor de combate todavía no cubre el daño mínimo/no letal que puede provocar un penalizador al daño. Es una limitación explícita de implementación, no un requisito general del guerrero. Otras razas, clases, niveles, armas a distancia, conjuros, arquetipos, envejecimiento y subida de nivel siguen pendientes.

## Del creador a la partida

Al confirmar se crea una ficha propia, se selecciona para hablar y mover, y se abre su hoja calculada con botones de tirada. En combate puede atacar usando el recorrido básico ya implementado. El anfitrión puede crear también un guerrero adversario con el mismo asistente; esto permite preparar una prueba de combate sin fichas manuales, pero no certifica el equilibrio del encuentro ni calcula su VD/PX.

El servidor recalcula y valida todas las elecciones: los totales de la vista previa no son autoridad. Se guardan elecciones y desglose con la ficha para revisarlos; se conservan en exportación/importación. No se alteran personajes antiguos. La edición manual avanzada de una ficha generada conserva su procedencia y marca que ya no está bajo cálculo automático; no se muestran totales anteriores como si siguieran recalculándose.

## Ahorro y borradores

La vista previa utiliza un catálogo estático y cálculo local. Cambiar pasos, características, equipo o elecciones no llama a Claude ni genera acciones de campaña. Un borrador de la pestaña se conserva en sessionStorage, separado por campaña y jugador; se elimina al crear correctamente. La sincronización habitual de la mesa continúa con su política existente. Confirmar usa una sola acción persistida y su deduplicación habitual, sin nueva colección o servicio.

La creación no utiliza IA ni consulta manuales remotos. Sus datos de auditoría se omiten del contexto de Claude porque duplican la ficha calculada; el director sigue recibiendo los atributos útiles para jugar. No se han creado partidas ni personajes de prueba en Firebase de producción.

## Fuentes y verificación

Datos contrastados en Reglas básicas local: PDF pp.16–18, características y compra; p.25, humanos; p.59, guerrero; p.87, habilidades; pp.127, 131–132, 136–138, dotes; pp.141–144 y 152, riqueza/armas/armaduras; equipo y atuendo en el capítulo 6; pp.170–171, carga. El catálogo contiene una selección de datos y fórmulas, no una copia de los manuales. El peso y precio del atuendo se contrastaron además con la [entrada de equipo de Pathfinder](https://www.aonprd.com/EquipmentMiscDisplay.aspx?ItemName=Traveler%27s+outfit).

Las pruebas comprueban cálculos conocidos, prerrequisitos, presupuesto, propiedad, adversarios, atributos manipulados, conservación de la procedencia y ataque real del motor con fichas generadas. Se contrastan 72 combinaciones de la vista previa JavaScript con el cálculo Python del servidor. Playwright recorre creación, presupuesto inválido, una única confirmación, tirada desde ficha, recarga, todos los pasos a 390×844, creación de adversario y ataque, sin introducir estadísticas manuales ni consumir IA.
