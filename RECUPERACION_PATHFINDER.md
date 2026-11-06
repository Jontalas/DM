# Recuperación Pathfinder: contrato en desarrollo

Base de consciencia verificada:587 pruebas completas con emulador sin omisiones (209,027s), tres navegadores afectados correctos. No hay acción horaria expuesta todavía. Siguiente recorrido: un PJ inconsciente y un PNJ consciente que espera por conducta escrita de una nueva versión de escena; el motor debe resolver las horas hasta consciencia o muerte en una confirmación, sin pedir al jugador administración por hora. Varios pacientes requieren programar sus instantes relativos y quedan fuera de ese primer recorrido; no avanzar su reloj omitiendo pruebas.

Fuentes originales comprobadas visualmente: Reglas básicas Devir, PDF190/folio189, PDF191/folio190 y PDF192/folio191. No son consultas remotas por acción. La escena de encuentro publicada no incluye todavía recuperación horaria.

`pf_recovery.consciousness_check` calcula una prueba de Constitución CD10 tras una hora, con penalizador igual a los PG negativos.20 natural tiene éxito;1 natural no implica fallo automático. Con ayuda un fallo no reduce PG; sin ayuda pierde1PG y puede morir al alcanzar −Constitución. Un éxito recupera consciencia, sin curar PG. La función es pura y no está conectada a una acción horaria: no avanza tiempo, tira dados ni cambia fichas.

Integración local posterior: la estabilización natural y los primeros auxilios efectivos registran `recoveryCare` con asistencia conocida y ronda. Una nueva herida o corrección excepcional de PG retira ese registro; no se certifica como curación conocida una edición manual. La copia valida el registro si existe y conserva su ausencia en partidas antiguas, sin inventar asistencia. Esto no activa todavía recuperación horaria ni modifica el estado de consciencia.

Antes de conectar el cálculo:

**Ampliación local en verificación:** `recoveryState` conserva horas, consciencia y última prueba comprobable, sin sustituir `recoveryCare`v1. La copia recalcula esa prueba y rechaza discrepancias; una herida nueva retira ambos registros. El motor distingue consciente/incapacitado con PG negativos: puede mover o atacar, no ambas acciones; atacar o auxiliar cuesta1PG y puede volverlo moribundo. Pruebas preparadas y presentación de ficha/ataque distinguen ese estado. Las tácticas pausan si solo queda un objetivo consciente con PG negativos, porque atacarlo sigue fuera de su perfil básico. No se presume cobertura completa.

`apply_hour` es un helper interno para el futuro controlador del tiempo; no constituye una acción expuesta ni avanza el reloj del mundo.66 pruebas afectadas correctas, incluidas dos HTTP/Waitress de copia consciente y rechazo de prueba alterada. La prueba HTTP prepara la hora internamente como fixture, no simula una interfaz horaria inexistente. La regresión completa y navegadores están en comprobación antes de respaldar.

- Registrar ayuda efectiva de primeros auxilios o curación en el episodio actual. No deducirla de estar estable ni tratar un dato ausente en copias antiguas como ayuda o ausencia de ayuda conocidas. Iniciar un episodio nuevo tras nuevas heridas.
- Representar consciencia por separado de los PG. Un paciente consciente con PG negativos está incapacitado: una acción estándar o movimiento por turno, sin ambas, y una acción fatigosa cuesta1PG salvo la excepción reglamentaria de curación. Daño posterior puede volverlo moribundo. Revisar ataques, movimiento, pruebas, turnos, tácticas, interfaz y copias juntos.
- Avanzar un reloj de ficción compartido y comprobar a todos los pacientes afectados por esa hora. No avanzar solo el reloj de uno ni usar la hora real del servidor como sustituto. El jugador consciente elige esperar; el inconsciente no toma decisiones. La conducta de PNJ durante la espera debe estar preparada y distinguida de reglas.
- Confirmar tiradas, reloj, pérdida de PG y consciencia en una misma acción duradera. Probar fallo de commit, recuperación con cliente nuevo, duplicado, permisos y copia antes de activar la interfaz.
- Recuperación natural, descanso8h y prueba diaria sin ayuda tienen reglas distintas, todavía pendientes. No conceder PG por superar la prueba de consciencia.

Las pruebas del cálculo recorren todos los dados, PG negativos legales y varias Constituciones, incluidos muerte por fallo sin ayuda y1 natural exitoso. Esta evidencia no acredita una recuperación jugable ni autoriza a mostrarla como disponible.
