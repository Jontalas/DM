# Primer bloque de combate automático

El tablero incorpora **Tirar ataque y resolver**. El jugador elige su personaje y un adversario adyacente; el servidor tira los dados, determina el impacto, confirma críticos, aplica daño y gasta la acción estándar en una sola acción persistida. No usa Claude ni consulta los manuales remotos para calcular reglas.

## Paso de 5 pies elegido por el jugador · patio 1.16

El propietario del PJ puede elegir «Dar paso de 5 pies» después de marcar una casilla adyacente. Es una acción explícita: un recorrido normal no se convierte silenciosamente en paso. El servidor valida la geometría, el turno, la propiedad y el estado; conserva las acciones estándar y de movimiento. No causa ataques de oportunidad, daño por incapacidad, tiradas ni avance del reloj. Una marca separada de las acciones gastadas impide repetirlo o realizar otro desplazamiento hasta el próximo turno propio; se conserva en copias y se elimina al cerrar el combate.

Fuentes originales comprobadas visualmente: Reglas básicas en castellano, PDF184/folio183 (tabla8-2: ninguna acción, sin AdO), PDF190/folio189 (un paso por asalto sin otro movimiento, velocidad normal superior a5pies, terreno/visibilidad/modos) y PDF194/folio193 (diagonales y esquinas). La incapacidad reduce la distancia de una acción de movimiento, no la velocidad normal usada para este requisito.

Cobertura acotada al nuevo patio1.16: combate individual preparado, luz normal, movimiento terrestre, origen y destino despejados, dos participantes presentes y sin condiciones o consecuencias pendientes. No automatiza el paso del PNJ. No ofrece pasos tras una acción de movimiento o asalto completo manual, porque no queda verificado si hubo desplazamiento: es un límite del motor, no una prohibición de Pathfinder. Retirada, AdO generales, oscuridad, terreno difícil, acciones preparadas y movimiento especial siguen pendientes. Versiones1.0–1.15 congeladas, sin migrar partidas.

La previsualización, selección y ayuda usan el estado ya cargado: cero IA, dados o acceso remoto. Confirmar utiliza el circuito persistente existente, una actualización de estado con recibo idempotente; no se presenta como gratuito en Firestore. Pruebas locales: reglas/límites, permisos, fallo atómico y reintento frío, copia, combinación con ataque/auxilio y recorrido guiado completo con teclado/móvil.

## Preparación

Fuera del combate, activar en las fichas participantes «Ataque cuerpo a cuerpo automático» y preparar los totales del arma: ataque, daño `NdM` o `NdM+bonificador`, CA normal, CA desprevenido, amenaza de crítico y multiplicador. Los totales ya incluyen los modificadores del arma y del personaje; no se añaden otra vez Fuerza ni ataque base. El perfil declara un arma empuñada de alcance de 5 pies, daño letal simple, criaturas de una casilla y ausencia de excepciones especiales.

Los perfiles anteriores se conservan sin migración obligatoria. Las fichas sin perfil continúan funcionando con las herramientas existentes. Un combate que ya estaba activo antes de esta versión debe finalizarse y reiniciarse para registrar quién ha tenido su primer turno; no se adivina ese dato.

## Resoluciones implementadas

- Propiedad del personaje, iniciativa y turno; un ataque consume la acción estándar y no se repite tras reenvío del mismo identificador.
- Alcance adyacente de 5 pies y adversarios de distinto bando.
- `d20 + ataque` frente a CA; 1 natural falla y 20 natural impacta. Antes del primer turno del defensor se usa su CA desprevenido declarada.
- Flanqueo +2 cuando un aliado armado con perfil, consciente y sin condiciones ocupa la casilla adyacente opuesta al atacante respecto del objetivo.
- Amenaza de crítico únicamente si el ataque impacta, confirmación con los mismos modificadores, tiradas de daño repetidas según el multiplicador y multiplicación del bonificador fijo.
- Daño, PG y estados consciente/incapacitado/moribundo/muerto según Constitución. Un atacante a 0 PG solo puede gastar una acción de movimiento o estándar; atacar le resta 1 PG al terminar, incluso si falla.
- En el turno siguiente de un personaje moribundo con perfil, sin condiciones especiales: prueba de Constitución CD 10 con penalizador igual a los PG negativos; 20 natural estabiliza, fallo pierde 1 PG. Un estable no repite la prueba y un muerto no la realiza. La curación registrada estabiliza; recibir daño elimina la estabilidad.
- Historial con dados, modificadores, CA aplicada, flanqueo, confirmación y resultado. El anfitrión también puede registrar dados físicos verificados mediante la API; los invitados usan los dados del servidor para este recorrido.

Verificación en los originales locales: Reglas básicas PDF pp.179–181 (iniciativa, CA, ataque y daño), p.183 (acción estándar), p.185 (críticos), pp.190–191 (heridas y estabilización). Los personajes conservan su orden incluso cuando no pueden actuar.

## Cobertura pendiente

Preparación automática de personajes y encuentros, interpretación de declaraciones libres como acciones mecánicas, tácticas de enemigos fuera del perfil básico, ataques de oportunidad, ataque completo, combate a distancia, conjuros, maniobras, cobertura, ocultación, tamaños y alcances especiales, condiciones, daño no letal, daño adicional, resistencia/reducción de daño y reglas de clase/dotes. El perfil actual no admite penalizadores en la expresión de daño porque los resultados inferiores a 1 implican reglas de daño no letal todavía no implementadas.

El motor rechaza ataques con condiciones anotadas, objetivos caídos o muros cercanos que puedan implicar cobertura. Se deriva a resolución excepcional; no se presenta una regla no implementada como automatizada. Las condiciones especiales también impiden resolver automáticamente la estabilización. Los movimientos de jugadores mantienen la revisión existente de ataques de oportunidad. Los adversarios básicos pueden actuar automáticamente sin IA, con rutas conservadoras que no abandonan casillas posiblemente amenazadas. Las excepciones pausan su turno y permiten al anfitrión tomar el control. Consulta [MESA_VIRTUAL.md](MESA_VIRTUAL.md).

No es todavía un combate completo de Pathfinder ni la versión final del juego. La preparación de fichas y las excepciones pendientes siguen requiriendo intervención humana.

## Pruebas y coste

```powershell
.\.venv\Scripts\python.exe -m unittest discover
node --check static/app.js
node test_sync.cjs
# Requiere Playwright instalado como herramienta local, no en producción:
# npm.cmd install --prefix .deps/browser-tests --no-audit --no-fund playwright
node test_browser.cjs
```

Las pruebas del navegador lanzan un servidor desechable con datos sintéticos, dados predecibles y dos sesiones aisladas. Nunca se importa ese almacenamiento ni se sustituyen los dados en producción. La suite Python usa el emulador oficial cuando está configurado `FIRESTORE_EMULATOR_HOST`; sin él se omiten sus pruebas específicas y el HTTP usa el doble de prueba explícito.

Cada ataque confirmado agrupa daño, gasto de acción y registro en una sola actualización de campaña, con las operaciones de persistencia ya utilizadas por las demás acciones. Cero llamadas de IA y cero consultas de reglas a Firebase por ataque. Continúan las lecturas de sesión/estado y escrituras de instantánea/metadatos/marcador; no es una acción gratuita de Firestore.

Se corrigió además la confirmación concurrente: el estado y el marcador se escriben en un mismo lote atómico condicionado a la fecha exacta de actualización del documento leído. Un conflicto devuelve el resultado previo si el identificador ya se confirmó, o solicita revisar la acción frente al nuevo estado. No se reejecutan dados ni IA, ni se mantienen bloqueos de lectura transaccionales mientras compiten dos confirmaciones.
