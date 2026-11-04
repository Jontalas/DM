# Adaptador experimental de Cairn 1e

**No disponible para jugar ni seleccionable.** El registro de producción sigue ofreciendo únicamente Pathfinder 1e con cobertura parcial. Este trabajo no adapta las reglas de Pathfinder ni reutiliza sus modificadores.

## Fuentes y atribución

Cairn, de Yochai Gal, SRD de primera edición v1.0: [fuente oficial](https://cairnrpg.com/first-edition/cairn-srd/) y [repositorio oficial](https://github.com/yochaigal/cairn). La fuente declara [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), con [texto de licencia](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en). Consulta del 4 de noviembre de 2026; el manifiesto rules_sources/cairn-1e.json conserva el hash del original local.

systems/cairn_1e.py es una implementación nueva de aritmética determinista con validación y trazabilidad, basada en esas reglas. Ese archivo y sus descripciones reglamentarias se distribuyen bajo CC BY-SA 4.0, conservando atribución y aviso de cambios. Este aviso no cambia la licencia del resto de la aplicación ni atribuye al autor del juego aprobación de este proyecto. No se ha añadido una copia del SRD completo al repositorio.

## Primer bloque comprobado

Secciones originales: Character Creation / Name, Background & Traits; Ability Scores; Hit Protection; Starting Gear (introducción); Rules / Saves. Son referencias HTML/Markdown con encabezados, sin paginación PDF inventada.

El cálculo inicial suma tres d6 por STR, DEX y WIL, un d6 de protección, tres d6 de oro y dos d20 más diez de edad. Admite el intercambio opcional de dos resultados iniciales. Una salvación compara d20 con la característica, con éxito en 1 y fallo en 20. No decide por sí misma si una situación exige tirada ni aplica consecuencias.

No se crea todavía una ficha jugable: faltan identidad, trasfondo, rasgos, equipo, inventario, consecuencias, persistencia e interfaz propias. `creation.complete` permanece en falso. No hay rutas HTTP nuevas ni registro del adaptador como disponible. Las funciones no llaman a IA, base de datos, red o RNG; reciben resultados de dados que una futura capa de servidor deberá generar y confirmar de forma atómica.

Ampliación: ya existen catálogo local e intérprete determinista para las 14 tablas de nombres, apellidos, trasfondos y rasgos. Conservan los valores originales en inglés, resultados y atribución; no son todavía un creador integrado. Las 180 entradas se extrajeron de la copia HTML oficial cuyo hash coincide con el manifiesto. Se revisaron visualmente los fragmentos originales con presentación legible (sin modificar las celdas), sin afirmar una nueva observación en vivo de la web. Las imágenes quedan en `.deps/cairn-original-tables-1.png` a `-3.png`; el script de extracción es reproducible y bloquea la red. `systems/cairn_1e_tables.json` conserva licencia CC BY-SA 4.0, autor y aviso de cambios. La interpretación de rasgos no impone decisiones, pensamientos ni emociones al personaje.

test_cairn_1e.py verifica el ejemplo de intercambio del SRD, conservación de resultados, dados inválidos, separación de sistemas y los veinte resultados de salvación para valores de característica de 0 a 24. Las pruebas no demuestran un recorrido de juego completo ni verificación de los capítulos restantes.
