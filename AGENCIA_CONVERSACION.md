# Agencia al declarar acciones y diálogo

El propietario conserva las decisiones y palabras de su PJ. En Pathfinder, una declaración `talk` con personaje explícito y tipo `action` o `dialogue` exige su propietario, también cuando quien envía es anfitrión. El rechazo ocurre antes de registrar el mensaje, reservar una inferencia o guardar la campaña. La administración excepcional de fichas y las notas `ooc`/privadas conservan sus permisos anteriores; el anfitrión conserva la interpretación manual de PNJ.

El selector muestra las opciones permitidas según el tipo de mensaje. Al pasar de una nota administrativa atribuida a otro PJ a una acción, vuelve al nombre del participante. Cambiar el selector es local: no llama a IA ni escribe datos remotos.

Verificación: tres pruebas de motor, una HTTP con Waitress/Firestore emulado (acciones y diálogos, director activado/desactivado, ningún proveedor ni commit ante rechazo), y navegador con dos participantes. El navegador comprueba selección local sin POST, notas administrativas y declaración del propietario en pantalla móvil táctil. No se ha solicitado una inferencia real para esta protección de permisos. No garantiza que el modelo interprete correctamente toda intención semántica escrita en texto libre.
