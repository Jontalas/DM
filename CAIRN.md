# Adaptador experimental de Cairn 1e

**No disponible para jugar ni seleccionable.** El registro de producción sigue ofreciendo únicamente Pathfinder 1e con cobertura parcial. Este trabajo no adapta las reglas de Pathfinder ni reutiliza sus modificadores.

Estado actual: el creador experimental ya permite confirmar, consultar, recuperar y exportar/importar personajes iniciales desde la interfaz común. Faltan las acciones, consecuencias y narración propias para completar un recorrido jugable y habilitar el sistema. Los apartados siguientes conservan la evolución y los límites de cada bloque; las ampliaciones posteriores sustituyen los avisos históricos de confirmación pendiente.

## Fuentes y atribución

Cairn, de Yochai Gal, SRD de primera edición v1.0: [fuente oficial](https://cairnrpg.com/first-edition/cairn-srd/) y [repositorio oficial](https://github.com/yochaigal/cairn). La fuente declara [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), con [texto de licencia](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en). Consulta del 4 de noviembre de 2026; el manifiesto rules_sources/cairn-1e.json conserva el hash del original local.

systems/cairn_1e.py es una implementación nueva de aritmética determinista con validación y trazabilidad, basada en esas reglas. Ese archivo y sus descripciones reglamentarias se distribuyen bajo CC BY-SA 4.0, conservando atribución y aviso de cambios. Este aviso no cambia la licencia del resto de la aplicación ni atribuye al autor del juego aprobación de este proyecto. No se ha añadido una copia del SRD completo al repositorio.

## Primer bloque comprobado

Secciones originales: Character Creation / Name, Background & Traits; Ability Scores; Hit Protection; Starting Gear (introducción); Rules / Saves. Son referencias HTML/Markdown con encabezados, sin paginación PDF inventada.

El cálculo inicial suma tres d6 por STR, DEX y WIL, un d6 de protección, tres d6 de oro y dos d20 más diez de edad. Admite el intercambio opcional de dos resultados iniciales. Una salvación compara d20 con la característica, con éxito en 1 y fallo en 20. No decide por sí misma si una situación exige tirada ni aplica consecuencias.

No se crea todavía una ficha jugable: faltan identidad, trasfondo, rasgos, equipo, inventario, consecuencias, persistencia e interfaz propias. `creation.complete` permanece en falso. No hay rutas HTTP nuevas ni registro del adaptador como disponible. Las funciones no llaman a IA, base de datos, red o RNG; reciben resultados de dados que una futura capa de servidor deberá generar y confirmar de forma atómica.

Ampliación: ya existen catálogo local e intérprete determinista para las 14 tablas de nombres, apellidos, trasfondos y rasgos. Conservan los valores originales en inglés, resultados y atribución; no son todavía un creador integrado. Las 180 entradas se extrajeron de la copia HTML oficial cuyo hash coincide con el manifiesto. Se revisaron visualmente los fragmentos originales con presentación legible (sin modificar las celdas), sin afirmar una nueva observación en vivo de la web. Las imágenes quedan en `.deps/cairn-original-tables-1.png` a `-3.png`; el script de extracción es reproducible y bloquea la red. `systems/cairn_1e_tables.json` conserva licencia CC BY-SA 4.0, autor y aviso de cambios. La interpretación de rasgos no impone decisiones, pensamientos ni emociones al personaje.

test_cairn_1e.py verifica el ejemplo de intercambio del SRD, conservación de resultados, dados inválidos, separación de sistemas y los veinte resultados de salvación para valores de característica de 0 a 24. Las pruebas no demuestran un recorrido de juego completo ni verificación de los capítulos restantes.

## Equipo e inventario en desarrollo

El catálogo extraído contiene ahora 22 tablas (420 resultados): se añadieron rangos de equipo inicial, herramientas, objetos y títulos de los cien grimorios. Revisadas visualmente las imágenes privadas `cairn-original-tables-4.png` a `-7.png`, que incluyen además las tablas originales de armaduras y armas con daño y volumen. Se ha comprobado el orden por resultado, incluidos los extremos de los intervalos y los saltos entre columnas. No se han implementado los efectos de los cien conjuros.

`systems/cairn_inventory.py`, con el mismo aviso de atribución y licencia, calcula espacios y armadura desde un catálogo, rechaza estadísticas añadidas por el cliente y conserva los originales. Equipo guardado fuera no cuenta; protecciones transportadas no suman armadura. Llenar diez espacios reduce protección a cero; retirar equipo no cura ni genera cicatrices. El cambio es puro y no escribe hasta que exista la futura acción validada de persistencia.

Límites pendientes antes de habilitar el sistema: transporte del carro y su reparto de carga; agrupación de objetos pequeños y monedas; colocación fina en cuerpo/mochila; selección de equipo inicial y objetos que se dejan; uso de manos y resolución contextual de las armas; efectos especiales y conjuros. No se convierte automáticamente «voluminoso» en una regla universal de dos manos: el núcleo rechaza equipar un arma hasta resolver ese contexto, aunque ya puede transportarla y consultar sus dados/espacios verificados. La combinación de protecciones repetidas también exige resolución explícita. Estos rechazos describen cobertura incompleta del adaptador, no prohibiciones atribuidas al SRD.

La FAQ oficial de primera edición se consultó buscando aclaraciones sobre manos, monedas, carro y volumen; no se encontró allí una regla específica que resolviera esos casos. No se importaron reglas de Barebones ni de segunda edición. Continúa el trabajo independiente de creador y resolución; no hay una pregunta imprescindible para el usuario en este punto.

## Borrador persistente del creador

`systems/cairn_creator.py` genera resultados una sola vez y reconstruye las vistas previas desde ellos. Mantiene separadas las tiradas iniciales y las elecciones posteriores de nombre/trasfondo, intercambio y equipo. Los rasgos originales se conservan como descriptores, sin imponer conducta al personaje. Las armas ofrecidas proceden exclusivamente de la fila obtenida; casco y escudo de un resultado combinado se conservan como objetos distintos. Un resultado «None» no se vuelve a tirar ni se sustituye por equipo gratuito.

Cuando el objeto adicional exige elegir entre dos tablas, se solicita esa decisión antes de tirar en la tabla elegida. Los resultados de tabla única se generan automáticamente con el dado correspondiente, incluido d100 para el título del grimorio. La elección resuelta no se puede repetir al recuperar o revisar el borrador.

La frontera de acciones del adaptador obtiene el propietario de la identidad de servidor, rechaza estadísticas/propietarios enviados por el cliente y evita abrir otro borrador cuando ya existe uno. Las vistas previas no usan RNG ni escriben. Esta frontera aún no está conectada a las rutas HTTP: la deduplicación de acciones y la confirmación transaccional del servidor existente deberán envolverla al integrarla. Se probó la recuperación de tiradas y elección adicional en el emulador oficial de Firestore, no en producción.

El resultado sigue marcado incompleto mientras falte integración del adaptador, aunque se hayan resuelto sus opciones. No se ha registrado Cairn ni se ha construido una interfaz alternativa que eluda las validaciones del servidor. Siguiente integración: despacho de acciones por sistema, creador visible con recuperación y confirmación conjunta, y resolución/narración propias antes de habilitar un recorrido de juego.

## Integración experimental en la mesa común

El servidor ya despacha operaciones mediante `rulesets.adapter`, después de comprobar disponibilidad, versión y marcador de acción. Pathfinder conserva su recorrido existente; el adaptador Cairn tiene un estado propio sin clases, niveles, reserva TREY ni presupuesto de combate Pathfinder. Crear y resolver la tabla adicional pasan por `/api/action`, permisos y confirmación atómica comunes. Las consultas narrativas de Pathfinder no se ejecutan en Cairn. Una copia de campaña no puede cambiar silenciosamente de sistema.

Esta conexión se ha probado inyectando disponibilidad exclusivamente en los procesos de prueba, con HTTP, Waitress y emulador oficial. La lista de producción **no registra Cairn**. Ningún parámetro de petición ni variable del arranque productivo activa esta disponibilidad experimental. La restauración completa de campañas Cairn sigue pendiente y se rechaza expresamente.

El creador experimental usa la misma cabecera, biblioteca y control de envíos de la aplicación, con presentación propia para STR/DEX/WIL, protección y equipo. Su catálogo se obtiene una vez por carga de página desde `/api/system-resources`, sin Firebase ni IA. El recurso incluye atribución y licencia. Las elecciones y cálculos se resuelven localmente; no existe una petición de vista previa por cada cambio. Los dados permanecen en el servidor y las elecciones todavía sin confirmar en almacenamiento local. Las actualizaciones ajenas no reconstruyen un formulario cuyo borrador propio no cambió.

La paridad de cálculo JavaScript/Python se comprueba en 16 combinaciones de tablas de arma/objeto adicional, orden de claves de transmisión, identidad, intercambio y disposición. Playwright verifica dos acciones iniciales, cero acciones/descargas de catálogo al revisar, recarga conservando los dados y elecciones, pantalla de 390×844, regreso a Pathfinder y salida durante una carga de catálogo retrasada. La captura móvil se inspeccionó. Se conservan las pruebas existentes del creador y biblioteca de Pathfinder. Todavía no hay botón de confirmación ni partida Cairn: el aviso de preparación es explícito. Lo siguiente es completar confirmación, hoja, importación y resolución/narración propias, manteniendo la barrera de disponibilidad hasta probar el recorrido.

## Confirmación, hoja y recuperación

La confirmación ya está conectada: el cliente envía elecciones, el servidor reconstruye la ficha desde el borrador y rechaza estadísticas añadidas, opciones incompletas o equipo fuera de los resultados. Solo se asigna el identificador y se retira el borrador después de validar. Todo se confirma con el marcador de acción y CAS comunes. `creation.complete` acredita el cierre del creador, no la disponibilidad de todas las reglas ni del adaptador de juego. Cada borrador nuevo recibe identidad propia, de modo que las elecciones locales de otro personaje no se reutilizan accidentalmente.

La hoja presenta STR/DEX/WIL, protección actual/máxima, armadura, espacios, oro, edad, inventario y origen de la creación. Cero protección no se representa como muerte. No se inventan raza, clase o nivel para adaptar el personaje a la biblioteca: los accesos Cairn conservan únicamente identidad y trasfondo. La biblioteca permite abrir su ficha original, pero no ofrece copias iniciales entre sistemas. El origen privado de creación no se incluye en el estado enviado a otros jugadores.

Exportar guarda la copia completa de la campaña y debe mantenerse privado: el anfitrión tiene acceso administrativo a ese archivo, incluidos borradores que no recibe al consultar el estado público. Importar valida consistencia de fichas, originales de creación, elecciones, duplicados y estructura. Reasigna al anfitrión las fichas según el contrato explícito de importación. Todos los borradores pendientes se conservan en un archivo de importación; el anfitrión recupera uno cada vez, sin sobrescribir el que ya controla. La importación no prueba autenticidad criptográfica de los dados de un archivo externo; comprueba su coherencia interna. Por ahora solo se admiten fichas iniciales canónicas: todavía no existe progreso mecánico de Cairn que recuperar.

Playwright simula perder la respuesta después de que el servidor confirme: el envío pendiente conserva su identificador y, al recargar, recupera una sola ficha. También comprueba hoja sin clases/niveles, biblioteca entre sistemas, elecciones locales, vista móvil y salida durante carga lenta. Se corrigieron los selectores y la espera de cambio de campaña de la prueba, que inicialmente observaba la biblioteca todavía abierta. Se actualiza la cabecera al entrar en el sistema conocido sin esperar su catálogo. Suite completa actual: **218 pruebas con el emulador oficial de Firestore, sin omisiones**; además pasan los recorridos de navegador de Cairn, creador Pathfinder y biblioteca Pathfinder. Sin inferencias de IA nuevas ni despliegue del adaptador experimental.
