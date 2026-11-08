# Auxilio automático de la guardiana

La escena original1.14 incorpora una guardiana que intenta estabilizar al PJ cuando queda moribundo. La decisión pertenece al PNJ y está fijada en la preparación: no elige acciones, descanso o palabras por el personaje del jugador. Necesita PG positivos, contacto adyacente y su próxima acción estándar disponible del primer combate corto. No se mueve ni vuelve a atacar al caído. El auxilio puede fallar; el PJ puede estabilizarse por sí mismo o morir antes de que ella pueda ayudar.

## Fuentes y variante

Original Devir Reglas básicas, erratas1.4: PDF90/folio89, tabla4-3 (Curar sin entrenamiento, Sabiduría, sin penalizador de armadura); PDF93/92 (primeros auxilios CD15, estabilización sin recuperar PG); PDF94/93 (acción estándar, reintentos con paciente vivo, equipo de sanador+2); PDF190–191/189–190 (incapacidad y estabilización, ConCD10 en iniciativa propia, penalizador por PG negativos,20natural siempre estabiliza y fallo pierde1PG). Las tablas y apartados se comprobaron visualmente en el original; capturas privadas fuera del repositorio.

El título de Curar en PDF93 dice Int, mientras la tabla4-3 y las listas usan Sab. Se conserva la interpretación Sab ya adoptada por el creador, por consistencia con tabla/listas. Es una discrepancia documentada del original, no una errata oficial atribuida al editor. La penalización por falta de equipo de PDF94 corresponde a tratar heridas mortales; no se traslada a primeros auxilios.

Nueva plantilla `pf1-common-speaking-first-aid-guard-1`, versión1.0.0: conserva todos los valores de la variante común6PG/CA15/Con10/Int12/Sab9 y añade únicamente Curar−1:0rangos, sin bonificador de clase ni equipo. Los tres rangos anteriores siguen asignados igual. No se añaden kit, conjuros ni curación. Las dos plantillas anteriores, sus huellas y las definiciones1.0–1.13 permanecen intactas. El goblin publicado conserva7PG y su procedencia; esta guardiana sigue siendo un PNJ original.

## Resolución y persistencia

`pf_first_aid` y `pf_stabilization` son operadores deterministas reutilizables. Validan antes de generar dados y devuelven copias. Primeros auxilios consume estándar, no daña al paciente por fallar y no recupera PG; ayudar a0 o negativo consciente cuesta1PG después, como antes. Una habilidad no gana éxito automático por20natural. La estabilización propia sí conserva la excepción expresa de20natural y puede causar muerte al fallar. Los relojes antiguos sin época mantienen care2, sin inventar care3.

`pf_npc_aid` ordena el episodio según ronda/iniciativa y presupuesto real. Una guardiana que acaba de atacar no usa otra estándar en ese turno: antes puede corresponder la comprobación del PJ. Si el PJ cae por esfuerzo en su propio turno, ella puede ayudar antes de su siguiente comprobación. Se conservan presupuesto y deuda de rápidas, sin movimiento ni ataques adicionales. El cambio se aplica al tablero vivo en el mismo objeto: evita que el controlador automático conserve un tablero antiguo activo y ejecute un turno extra.

El recibo `cronicas-pf-first-aid-episode-1` conserva inicio, dados ordenados y desenlace, ligado a definición y marcador de mensaje. Al importar se reproduce y se compara con perfil original, cuidados y desenlace. Recalcular una suma de comprobación no legaliza un modificador Curar falso. Un episodio con cero intentos no certifica asistencia: el PJ pudo estabilizarse antes. Un intento fallido tampoco la concede. El director recibe esta distinción y debe respetar los resultados, sin narrar curación.

La recuperación compartida2 admite al PJ asistido y usa `cronicas-pf-recovery-outcome-3`. Comprueba consciencia sin perder PG por fallos asistidos y se detiene, si sigue inconsciente, en la frontera de seis horas antes del descanso aún no cubierto. No cambia los recibos2 ni amplía el cálculo de curación natural. El formato de evolución médica `cronicas-pf-recovery-state-3` sigue siendo soporte interno distinto de este recibo3.

Al despertar,0PG o negativos conscientes pueden continuar la investigación1.14 únicamente con fichas originales y prueba actual exacta. Se conservan PG, cuidados, cinco pistas/tres escenas/regreso y decisiones del jugador. La interfaz mantiene visibles el motivo de un bloqueo y el estado actual. Los detalles de recuperación admiten hasta40 comprobaciones, el máximo ya validado por el reloj compartido, sin ocultar auditorías largas.

## Alcance y coste

Auxilio limitado al primer combate, comienzo hasta asalto550, dos participantes originales presentes, sin condiciones, correcciones de perfil, terreno especial o situaciones pendientes. La frontera es cobertura del motor, no regla Pathfinder. No cubre sangrado, cuidados a largo plazo, nuevos tratamientos posteriores, kit de sanador, otros tipos de curación, calendario general, recursos diarios o resurrección. La recuperación horaria del PJ sigue requiriendo armadura ligera; con cota se conservan el auxilio y el límite de recuperación, sin quitar ropa ni elegir sueño por él. La noche anterior no se amplía a negativos.

Todos los dados y consecuencias se agrupan en la acción original, sin IA por auxilio o por hora ni commits de campaña intermedios. La prueba HTTP verifica un solo commit y recuperación de los mismos dados tras fallo con cliente nuevo; duplicado y copia no repiten efectos. No se han generado inferencias reales nuevas para este bloque.

## Evidencia

849 pruebas completas correctas en216,345s, `.deps/npc-aid-final-tests.log`;65 afectadas puras y14 HTTP afectadas. Se comprueban iniciativa, estándar gastada, asistencia real frente a estabilización natural, muerte, límite de seis horas, cota intacta, copia, recibos falsos y conservación de versiones anteriores. Navegador desde creador legal: éxito, ayuda fallida seguida de estabilización natural, muerte y frontera; teclado/tacto/móvil, copia/recarga. Los casos continuables completan cinco pistas, tres escenas y regreso sin cambiar fichas ni cuidados. Dados simulados en estos navegadores; servidor de dados real en la prueba HTTP de recuperación. Espera declarada, recuperación compartida antigua y tregua/noche anteriores conservadas. La coherencia semántica real del director corregido sigue pendiente y no se deduce de esta regresión.
