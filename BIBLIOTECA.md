# Partidas y personajes guardados

## Qué se guarda

La campaña y el estado actual de sus personajes siguen en Firebase. «Mis partidas» conserva en el perfil del navegador un índice de accesos, títulos y personajes propios. Entrar en otra campaña deja de sustituir el único acceso recordado: se puede volver a cada partida y abrir la ficha original, recuperando su estado vigente del servidor.

La lista solo incluye personajes del jugador de ese acceso; el anfitrión no incorpora automáticamente personajes de invitados o enemigos a su biblioteca. No guarda secretos, notas privadas, memoria del director ni inventarios completos. Los metadatos son una caché y pueden estar desactualizados hasta abrir la partida.

Cada combinación de campaña y participante tiene su propia entrada. Los permisos se comprueban con el servidor al abrirla: el archivo local no puede conceder permisos de anfitrión ni acceso a una campaña ajena por cambiar un nombre o una marca local.

## Reutilizar un personaje

«Abrir personaje original» vuelve a la campaña donde vive y conserva heridas, recursos, equipo y progresión allí guardados.

«Crear copia inicial aquí» está disponible para personajes del creador sin edición manual y con sistema compatible. Crea una ficha nueva de nivel 1 en la campaña actual mediante el cálculo y la validación del servidor. Se conserva la campaña original; no se transfieren sus heridas, objetos adquiridos, experiencia ni progreso. El diálogo lo explica antes de crear. No se ofrece como migración de personajes avanzados o como sincronización entre campañas.

La biblioteca no añade opciones reglamentarias: utiliza las elecciones del bloque verificado de humanos guerreros de nivel 1 y rechaza plantillas incompatibles. Las fichas manuales se pueden abrir en su campaña, pero no se presentan como copias automáticamente recalculables.

## Recuperar accesos y privacidad

La lista pertenece al perfil del navegador, no a una cuenta global ni a una sincronización automática entre dispositivos. Para llevarla a otro perfil o dispositivo, «Guardar mis accesos» descarga un archivo privado y «Recuperar accesos» lo combina con la lista existente. El archivo contiene credenciales de entrada y debe guardarse privadamente; permite actuar con esos permisos. Importarlo no realiza consultas por cada campaña: se comprueba la elegida al abrirla.

Perder el almacenamiento del navegador sin copia de sus accesos puede impedir recuperar una credencial de anfitrión. Compartir un perfil del navegador comparte sus accesos; para jugadores independientes se siguen usando perfiles o navegadores separados. Esta entrega no introduce autenticación global de usuarios.

Se admiten hasta cien accesos por perfil. Datos locales corruptos no se sustituyen silenciosamente por una lista vacía. Si falla la caché, se mantiene el funcionamiento de la campaña y su persistencia remota. Un envío pendiente o una acción en curso impiden cambiar de campaña para no perder su identificador de recuperación.

## Coste y verificación

Consultar la biblioteca y abrir el diálogo no consume IA ni lee Firebase. Abrir una campaña hace una lectura normal de su estado; copiar un personaje usa una acción de creación ya existente. Actualizaciones sin cambios en los metadatos no reescriben la caché. No hay colección remota, consulta periódica ni servicio adicional para la biblioteca.

test_campaign_library.cjs comprueba privacidad, separación por propietario, compatibilidad, escritura solo al cambiar, conservación ante corrupción/cuota y validación de copias. test_library_browser.cjs recorre dos campañas, copia inicial calculada, heridas originales conservadas, archivo de accesos importado en otro perfil, protección de envíos pendientes, recarga y móvil. No utiliza inferencia real ni datos de producción.
