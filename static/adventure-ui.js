/* Adventure preparation is an explicit action; rendering and reading stay local. */
function renderAdventure(){
 const s=snapshot.state, host=!!snapshot.me.host, active=!!s.adventure;
 const ready=s.characters.some(c=>!c.enemy&&c.creation&&!c.creation.manualOverride&&c.hp>0&&!c.conditions?.trim());
 const entry=$('#adventureEntry');
 entry.hidden=active;
 entry.innerHTML=active?'':`<div class="card"><div class="eyebrow">LA PRIMERA PÁGINA</div><h3>El mundo espera a tu personaje</h3><p>${host?'Elige una aventura preparada o pide al director que cree una a partir de tu idea. Tú decides cómo actuar.':'El anfitrión puede iniciar la aventura cuando haya un personaje listo.'}</p>${host?`<button id="beginAdventure" class="primary" ${!ready||s.board.active?'disabled':''}>Elegir aventura</button><small>${!ready?'Crea primero un personaje con el asistente.':s.board.active?'Finaliza el combate para comenzar.':!model.aiConfigured?'Puedes jugar una aventura preparada; crear o adaptar una nueva requiere al director.':'El comienzo se guarda para continuar en otra sesión.'}</small>`:''}</div>`;
 if($('#beginAdventure'))$('#beginAdventure').onclick=()=>{
  modal(`<div class="eyebrow">UN NUEVO COMIENZO</div><h2>¿Qué historia te apetece vivir?</h2><form id="adventureForm"><label>Aventura<select name="source" aria-describedby="adventureSourceHint"><optgroup label="Aventuras preparadas"><option value="example">La carta perdida · investigación breve</option><option value="route">Los senderos del archivo · ruta individual</option></optgroup><optgroup label="Preparar otra historia"><option value="generated">Crear a partir de mi idea · usa IA</option><option value="text">Adaptar un texto breve · usa IA</option><option value="import">Usar una aventura JSON compatible</option></optgroup></select></label><p id="adventureChoiceDescription" role="status" aria-live="polite"></p><label id="premiseField">Premisa<textarea name="premise" required maxlength="2000" rows="4">${esc(s.goal)}</textarea></label><label id="moduleFileField" hidden>Archivo de aventura<input type="file" name="moduleFile" accept=".json,application/json"><small>Una escena cronicas-adventure-1 (64 KiB) o ruta individual cronicas-route-1 (192.000 bytes). Investigaciones tranquilas de Percepción. Usa contenido que tengas derecho a utilizar.</small></label><div id="sourceTextField" hidden><label>Texto de la aventura<textarea name="sourceText" maxlength="12000" rows="6" placeholder="Pega un fragmento de la aventura"></textarea></label><label>Cargar texto desde un archivo<input type="file" name="sourceFile" accept=".txt,.md,text/plain,text/markdown"></label><small>Hasta 12.000 caracteres en UTF-8. Usa contenido que tengas derecho a utilizar. La IA adaptará una sola situación a dos búsquedas de Percepción, sin peligros ni combate; no convierte la aventura completa. El texto se envía al director al comenzar y puede contener secretos. Se conserva la adaptación; guarda tu original aparte.</small></div><p id="adventureModeHint"></p><button class="primary">Preparar y comenzar</button><p id="adventureProgress" role="status" aria-live="polite"></p><small id="adventureSourceHint" role="status" aria-live="polite"></small></form>`);
  const updateSource=()=>{
   const choice=$('#adventureForm [name=source]').value;
   $('#adventureChoiceDescription').textContent={
    example:'Lucio ha perdido una carta en una posada. Una investigación tranquila en un único lugar: examina el entorno y decide qué hacer con lo que encuentres. Sin combate ni peligros.',
    route:'Busca un registro antiguo en un archivo. Elige entre salas, investiga y vuelve a lugares ya visitados. Ruta individual tranquila, sin combate ni peligros en los trayectos.',
    generated:'Describe qué te gustaría investigar. El director creará una sola situación tranquila con dos búsquedas de Percepción; todavía no genera una campaña completa ni un encuentro de combate.',
    text:'Aporta un fragmento que tengas derecho a utilizar. El director lo adaptará a una investigación breve; no importa ni convierte toda una campaña.',
    import:'Abre una investigación o ruta preparada para esta aplicación. Un documento o una aventura de otro formato necesita adaptación previa.'
   }[choice]||'';
   $('#premiseField').hidden=choice!=='generated';
   $('#adventureForm [name=premise]').required=choice==='generated';
   $('#sourceTextField').hidden=choice!=='text';
   $('#adventureForm [name=sourceText]').required=choice==='text';
   $('#moduleFileField').hidden=choice!=='import';
   $('#adventureForm [name=moduleFile]').required=choice==='import';
   const needsDirector=['generated','text'].includes(choice);
   $('#adventureForm button').disabled=needsDirector&&!model.aiConfigured;
   $('#adventureModeHint').textContent=needsDirector?'El director preparará el comienzo sin decidir las acciones de tu personaje.':'Se conserva la presentación original. Las pistas siguen pendientes hasta que decidas investigarlas.';
   $('#adventureSourceHint').textContent=needsDirector?(model.aiConfigured?'Crear o adaptar el comienzo usa el director de IA.':'El director no está disponible. Elige una aventura preparada.'):'El comienzo ya está escrito: no llama a IA. '+(model.aiConfigured?'Puedes pedir al director que intervenga durante la partida.':'Puedes investigar con las opciones de la escena; el director de IA no está disponible.');
  };
  $('#adventureForm [name=source]').onchange=updateSource;
  $('#adventureForm [name=source]').value='example';
  updateSource();
  $('#adventureForm [name=sourceFile]').onchange=run(async e=>{
   const file=e.target.files[0];if(!file)return;
   if(!/\.(txt|md)$/i.test(file.name)||file.size>48000)throw Error('Elige un archivo .txt o .md UTF-8 de hasta 48.000 bytes.');
   let text;try{text=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer())}catch{throw Error('El archivo debe estar codificado en UTF-8.')}
   if(!text.trim()||[...text].length>12000||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(text))throw Error('El documento debe contener texto legible, entre 1 y 12.000 caracteres.');
   $('#adventureForm [name=sourceText]').value=text;
  });
  $('#adventureForm').onsubmit=run(async e=>{
   const form=e.target,button=form.querySelector('button');button.disabled=true;
   $('#adventureProgress').textContent=['generated','text'].includes(form.elements.source.value)?'El director está preparando la aventura…':'Abriendo la aventura preparada…';
   try{
    const data={premise:form.elements.premise.value,structured:form.elements.source.value==='generated',worldMemoryContract:'structured-world-memory-1'};
    if(form.elements.source.value==='text'){
     data.sourceText=form.elements.sourceText.value.trim();
     if(!data.sourceText||[...data.sourceText].length>12000)throw Error('Aporta entre 1 y 12.000 caracteres de texto.');
     data.structured=true;
    }
    if(['example','route','import'].includes(form.elements.source.value))data.openingContract='authored-opening-1';
    if(form.elements.source.value==='route')data.moduleId='senderos-del-archivo';
    if(form.elements.source.value==='example')data.moduleId='la-carta-perdida';
    if(form.elements.source.value==='import'){
     const file=form.elements.moduleFile.files[0];if(!file||file.size>192000)throw Error('Elige un archivo JSON de hasta 192.000 bytes.');
     try{data.module=JSON.parse(await file.text())}catch{throw Error('El archivo no contiene JSON válido.')}
    }
    await act('start_adventure',data);$('#modal').close();chooseTab('story');
   }
   catch(error){$('#adventureProgress').textContent=error.message;throw error;}
   finally{updateSource();}
  });
 };
 const memory=$('#adventureMemory');memory.hidden=!active;
 $('#adventureSummary').textContent=s.adventure?.summary||'';
 $('#adventureObjectives').innerHTML=(s.objectives||[]).map(item=>`<li>${esc(item)}</li>`).join('');
 $('#adventureRevision').textContent=active?`Memoria de aventura · revisión ${s.adventure.revision}. Las tiradas y sus consecuencias se consultan en el registro.`:'';
 const privateMemory=$('#directorMemoryDetails');privateMemory.hidden=!host||!s.directorMemory;
 $('#directorMemoryText').textContent=host?s.directorMemory||'':'';
 const lastDirector=s.messages.findLastIndex(m=>m.kind==='director'&&!m.ooc);
 const results=s.messages.filter((m,i)=>i>lastDirector&&m.check);
 const ownsResult=host||results.some(m=>s.characters.some(c=>c.id===m.check.character&&c.owner===snapshot.me.id));
 const continuation=$('#continueAdventure');
 continuation.hidden=!active||!results.length||!ownsResult||s.pending.some(p=>p.check);
 continuation.disabled=!model.aiConfigured;
 const narrationHint=$('#continueAdventureHint');narrationHint.hidden=continuation.hidden;
 narrationHint.textContent=model.aiConfigured?'Opcional. Las tiradas ya están resueltas; puedes seguir jugando sin pedir esta narración.':'El director no está disponible. Puedes seguir con las opciones de la aventura, las fichas y los dados.';
 continuation.onclick=run(()=>act('continue_adventure'));
 renderInvestigation();
 renderPreparedPathfinderEncounter();
}

function preparedEncounterHelp(definition,actor){
 const limited=['single-unconscious-player-1','shared-patients-1','shared-patients-2'].includes(definition.recoveryScope)&&actor?.hp>=0&&actor?.creation?.choices?.armor==='scale';
 return `${limited?'<p class="notice recovery-limit">Si caes inconsciente con tu cota de escamas, la recuperación posterior necesitará una resolución excepcional. El juego conservará tu estado.</p>':''}<details class="encounter-help"><summary>Qué incluye este encuentro</summary><p>${esc(definition.coverage)}</p><p>Una persona juega con su personaje. Luz normal, patio abierto y sin sorpresa. La guardiana tiene su ficha preparada.</p><p>Su disposición a negociar pertenece a esta escena; otras conversaciones pueden necesitar una prueba de Diplomacia.</p></details>`;
}

function preparedEncounterHealthDescription(record,actor,npc){
 if(record.phase!=='defeated')return '';
 if(characterIsConscious(actor)){
  if(['shared-patients-1','shared-patients-2'].includes(record.definition.recoveryScope)&&npc&&!characterIsConscious(npc))return npc.hp<=-npc.abilities[2]?'Has recuperado la consciencia. La guardiana ha muerto; tú decides qué haces a continuación.':'Has recuperado la consciencia. La guardiana sigue inconsciente; tú decides qué haces a continuación.';
  return ['single-unconscious-player-1','shared-patients-1','shared-patients-2'].includes(record.definition.recoveryScope)?'Has recuperado la consciencia. La guardiana te permite retirarte; tú decides qué haces a continuación.':'Estás consciente. Consulta tus heridas en la ficha; tú decides qué haces a continuación.';
 }
 if(actor.hp<=-actor.abilities[2])return 'Tu personaje ha muerto por sus heridas. Puedes revisar lo ocurrido en el registro. Para empezar otra campaña, vuelve al inicio con «Salir».';
 if(record.recoveryLimit==='armor-rest')return 'Tu personaje está inconsciente y estable. La recuperación prolongada con su armadura requiere efectos de descanso aún pendientes. No se han avanzado horas de juego.';
 if(record.recoveryLimit==='shared-rest-boundary')return 'Tu personaje sigue inconsciente y estable. El reloj se ha detenido antes de un descanso que todavía no está cubierto. Se conservan las heridas y todas las comprobaciones resueltas.';
 return actor.stable?'Tu personaje sigue inconsciente y estable. La asistencia o recuperación de esta situación aún no está cubierta; no se inventan decisiones ni curación.':'Tu personaje sigue moribundo. Esta situación requiere una resolución excepcional; consulta la limitación en el registro.';
}

function renderPreparedPathfinderEncounter(){
 const s=snapshot.state,entry=$('#adventureEntry'),own=s.characters.filter(c=>!c.enemy&&c.owner===snapshot.me.id&&c.creation&&!c.creation.manualOverride);
 const record=s.pfEncounter;
 if(s.pfContinuation){entry.hidden=true;return;}
 if(record){
  entry.hidden=false;
  const mine=own.some(c=>c.id===record.character),definition=record.definition;
  const actor=s.characters.find(c=>c.id===record.character),patient=s.characters.find(c=>c.id===record.npc);
  const waiting=s.pfNpcRecoveryView;
  const waitDescription=waiting?.currentResult?(waiting.result.status==='conscious'?'La guardiana ha despertado. Sigue herida y permanece sentada y despierta en el patio; puedes decidir si continúas investigando.':waiting.result.status==='dead'?'La guardiana ha muerto por sus heridas durante la espera. Tu personaje conserva su estado; tú decides cómo continuar.':'La guardiana sigue inconsciente y estable. La espera se ha detenido antes de un descanso todavía no cubierto; las heridas y las comprobaciones se conservan.'):'';
  const description=waitDescription||(s.pfNightRestView?.completed&&['agreement','resolved'].includes(record.phase)?'El encuentro y la noche de descanso están resueltos. Consulta tu salud actual en la ficha y decide si continúas investigando.':preparedEncounterHealthDescription(record,actor,patient)|| (record.phase==='offered'?definition.description:record.phase==='agreement'?definition.agreement:record.phase==='resolved'?`Desenlace registrado: ${record.outcome.status==='stable'?'adversario inconsciente y estable':'muerte del adversario'}, con ${record.outcome.hp} PG. No se recuperan PG ni se mueve tu ficha. Tú decides qué haces después.`:record.phase==='defeated'?`Desenlace registrado del personaje: ${record.outcome.status==='dead'?'muerto':'inconsciente y estable'}, con ${record.outcome.hp} PG. Se conservan las heridas. Consulta el estado actual en tu ficha.`:'El combate está iniciado. La iniciativa, los ataques y el estado de los participantes se consultan en el tablero y el registro.'));
  entry.innerHTML=`<section class="card"><div class="eyebrow">ENCUENTRO PREPARADO · EXPERIMENTAL</div><h3>${esc(definition.title)}</h3><p>${esc(description)}</p>${record.phase==='offered'?`<p><strong>${mine?'Decide cómo responder.':'El propietario del personaje decide cómo responder.'}</strong></p><div class="toolbar"><button id="pfEncounterParley" ${mine?'':'disabled'}>Proponer el paso sin combatir</button><button id="pfEncounterCombat" ${mine?'':'disabled'}>Entrar en combate</button></div>`:''}${actor.hp<0&&characterIsConscious(actor)?'<p class="notice">Ahora estás consciente, con PG negativos. Puedes moverte o realizar una acción estándar, pero no ambas; una acción fatigosa cuesta 1 PG y puede hacerte caer de nuevo. No has recuperado PG.</p>':''}${record.recoveryOutcome?`<p>Tiempo transcurrido: ${record.recoveryOutcome.hours} ${record.recoveryOutcome.hours===1?'hora':'horas'}. Consulta las tiradas en el registro.</p>`:''}<div id="pfEncounterAid"></div>${preparedEncounterHelp(definition,actor)}</section>`;
  if(definition.continuation&&['agreement','resolved','defeated'].includes(record.phase)){
   const ready=mine&&!s.board.active&&canExplorePrepared(actor)&&(patient.hp>=0||patient.hp<=-patient.abilities[2]||waiting?.canContinue||s.pfLightExplorationView?.canExplore);
   const hint=!canExplorePrepared(actor)?'Esta versión aún no cubre investigar en tu estado.':patient.hp<0&&patient.hp>-patient.abilities[2]&&!(waiting?.canContinue||s.pfLightExplorationView?.canExplore)?'La guardiana sigue necesitando seguimiento de sus heridas.':'Puedes examinar el registro del banco sin abandonar el patio. No recuperas PG al continuar.';
   entry.querySelector('.card').insertAdjacentHTML('beforeend',`<p id="pfContinueHint">${esc(hint)}</p><button id="pfContinueScene" class="primary" aria-describedby="pfContinueHint" ${ready?'':'disabled'}>Investigar el registro del patio</button>`);
   $('#pfContinueScene').onclick=run(()=>act('continue_pf_encounter'));
  }
  const night=s.pfNightRestView;
  if(waiting&&record.phase==='resolved'&&patient.hp<0&&patient.hp>-patient.abilities[2]&&!waiting.result){
   const hint=!mine?'El propietario decide si su personaje espera.':waiting.reason||'El juego resolverá las comprobaciones cubiertas. Tu personaje permanece despierto; no se recuperan PG.';
   entry.querySelector('.card').insertAdjacentHTML('beforeend',`<h4>Esperar junto a la guardiana</h4><p>Está estable, pero aún no ha despertado. Puedes esperar para ver si recupera la consciencia.</p>${!waiting.assisted?'<p class="notice">Sin ayuda, cada comprobación fallida puede hacerle perder 1 PG y morir.</p>':''}<p id="pfNpcWaitHint">${esc(hint)}</p><button id="pfWaitNpcRecovery" aria-describedby="pfNpcWaitHint" ${mine&&!waiting.reason?'':'disabled'}>Esperar a que despierte</button><details><summary>Qué cubre la espera</summary><p>Hasta seis comprobaciones horarias desde la estabilización. Si sigue inconsciente al llegar al límite, se conserva el estado sin simular un descanso. No cura ni decide dormir por tu personaje.</p></details>`);
   $('#pfWaitNpcRecovery').onclick=run(()=>act('wait_pf_npc_recovery'));
  }
  if(s.pfCeasefireView&&record.phase==='combat'&&patient.hp>0&&(patient.hp<patient.maxHp||s.pfCeasefireView.disabledPlayerOffer)&&characterIsConscious(actor)){
   const reason=s.pfCeasefireView.reason,canAccept=mine&&!reason;
   entry.querySelector('.card').insertAdjacentHTML('beforeend',`<h4>Detener el enfrentamiento</h4><p>La guardiana${patient.hp<patient.maxHp?' herida':''} ofrece en ${esc((s.pfCeasefireView.offerLanguage||'Goblin').toLowerCase())} dejar de combatir y permitirte pasar. Tú decides si aceptas o sigues luchando.</p><p id="pfCeasefireHint">${esc(!mine?'El propietario del personaje decide si acepta.':reason||'Puedes responder con unas palabras, sin gastar tu acción estándar ni perder PG. Las heridas se conservan.')}</p><button id="pfAcceptCeasefire" aria-describedby="pfCeasefireHint" ${canAccept?'':'disabled'}>Aceptar la tregua</button>`);
   $('#pfAcceptCeasefire').onclick=run(()=>act('accept_pf_ceasefire'));
  }
  if(night&&['agreement','resolved'].includes(record.phase)){
   const result=night.result,canRest=mine&&!night.reason,removeArmor=night.armorPlan==='remove-and-reequip';
   const restText=removeArmor?'Puedes quitarte la cota, dormir 8 horas sin ella y volver a ponértela normalmente. Recuperas 1 PG por nivel, hasta tu máximo. Quitarla y equiparla suma 5 minutos, sin ayuda.':'Puedes dormir 8 horas sin interrupciones en el refugio del patio. Recuperas 1 PG por nivel, hasta tu máximo. La guardiana viva permanece despierta; no se cura.';
   entry.querySelector('.card').insertAdjacentHTML('beforeend',night.completed?
    `<p class="notice" id="pfRestResult">Has descansado 8 horas y recuperado ${Number(result.healing.amount)} PG.${result.seconds>28800?` Preparar la armadura ha añadido ${Number((result.seconds-28800)/60)} minutos.`:''} Tu salud actual está en la ficha.</p>`:
    `<details id="pfRestOptions"><summary>Descansar antes de continuar</summary><p>${esc(restText)}</p><p id="pfRestHint">${esc(!mine?'El propietario decide si su personaje duerme.':night.reason||'La noche pasa y tus heridas restantes se conservan. Esta ruta ofrece una única noche preparada.')}</p><button id="pfRestNight" aria-describedby="pfRestHint" ${canRest?'':'disabled'}>${removeArmor?'Quitarme la cota, dormir y volver a equiparme':'Dormir esta noche · 8 horas'}</button><details><summary>Reglas y límites del descanso</summary><p>${esc(definition.restPolicy)}</p><p>Curación natural: Reglas básicas, PDF p.192. Dormir con armadura ligera: PDF p.151.${night.armorPlan?' Quitar y poner la armadura normalmente sin ayuda: PDF p.154.':''} Esta opción no recupera recursos diarios ni resuelve pacientes negativos, fatiga u otras condiciones.</p></details></details>`);
   if($('#pfRestNight'))$('#pfRestNight').onclick=run(()=>act('rest_pf_night',night.armorPlan?{armorPlan:night.armorPlan}:{}));
  }
  if($('#pfEncounterParley'))$('#pfEncounterParley').onclick=run(()=>act('choose_pf_encounter',{choice:'parley'}));
  if($('#pfEncounterCombat'))$('#pfEncounterCombat').onclick=run(async()=>{await act('choose_pf_encounter',{choice:'combat'});chooseTab('board');});
  if(record.phase==='combat'&&s.board.active&&patient.hp<0&&!patient.stable&&patient.hp>-patient.abilities[2]){
   const turn=s.board.order[s.board.turn]?.id===actor.id,spent=s.board.spent[actor.id]||{},conscious=characterIsConscious(actor);
   const adjacent=Math.max(Math.abs(actor.x-patient.x),Math.abs(actor.y-patient.y))===1;
   const canAid=mine&&turn&&conscious&&adjacent&&!spent.standard&&!(actor.hp<=0&&spent.move),canWait=mine&&turn&&conscious;
   const hint=!turn?'Espera al turno de tu personaje.':spent.standard?'Ya has actuado. Termina tu turno para volver a intentar ayudar o elige esperar.':!adjacent?'Acércate a una casilla junto a la guardiana para ayudarla.':'Puedes intentar ayudarla ahora; el juego calcula la tirada por ti.';
   $('#pfEncounterAid').innerHTML=`<h4>La guardiana necesita auxilio</h4><p>Puedes intentar estabilizarla sin curar sus heridas. Si esperas sin ayudar, podría morir.</p>${actor.hp<=0?'<p class="notice">Estás incapacitado: ayudar cuesta 1 PG y te deja moribundo.</p>':''}<p id="pfAidHint" role="status">${esc(hint)}</p><form id="pfFirstAidForm"><button aria-describedby="pfAidHint" ${canAid?'':'disabled'}>Intentar primeros auxilios</button>${snapshot.me.host?'<details><summary>He tirado un d20 físico</summary><label>Resultado del dado<input name="physical" type="number" min="1" max="20" step="1" placeholder="Vacío: tira el juego"></label></details>':''}</form><button id="pfWaitStabilization" ${canWait?'':'disabled'}>Esperar sin ayudar</button><details><summary>Cómo funciona el auxilio</summary><p>Necesitas estar junto a ella y tener libre tu acción estándar. El juego tira y suma tu habilidad Curar: necesitas 15 para estabilizarla. No recupera PG. Si fallas, podrás intentarlo de nuevo en otro turno mientras siga viva.</p><p>Esperar resuelve sus pruebas de estabilización hasta que esté estable o muera. No cambia lo que decide tu personaje.</p></details>`;
   $('#pfFirstAidForm').onsubmit=run(async e=>{const raw=e.target.elements.physical?.value||'';await act('pf_first_aid',raw?{physical:Number(raw)}:{});});
   $('#pfWaitStabilization').onclick=run(()=>act('pf_wait_stabilization'));
  }else if(record.phase==='combat'&&!characterIsConscious(actor))$('#pfEncounterAid').innerHTML='<p class="notice">Tu personaje ha caído. Las condiciones o correcciones de esta mesa exceden el desenlace automático del encuentro; revisa la limitación registrada. No se simula su recuperación.</p>';
  return;
 }
 if(s.mode!=='solo'||s.adventure||s.adventureModule||s.adventureRoute||s.board.active||s.characters.length!==1||own.length!==1)return;
 entry.insertAdjacentHTML('beforeend','<section class="card"><h3>Un encuentro preparado</h3><p>Habla o combate para conseguir el paso. Después puedes investigar el patio y seguir las pistas. El juego prepara las fichas y calcula las reglas cubiertas.</p><button id="beginPreparedEncounter">Consultar El patio del peaje</button></section>');
 $('#beginPreparedEncounter').onclick=run(async()=>{
  const key=token+':'+snapshot.id,{encounters}=await api('/api/pf-encounters'),definition=encounters[0];
  if(token+':'+snapshot.id!==key)throw Error('La campaña ha cambiado; vuelve a abrir el encuentro.');
  const scopeHint=definition.restScope?'Recorrido experimental: tras resolver el encuentro puedes investigar o elegir una noche de descanso si no hay heridas o efectos pendientes de seguimiento. La cobertura real se explica al elegir.':'Encuentro básico experimental. Consulta la cobertura del recorrido antes de empezar.';
  modal(`<div class="eyebrow">ESCENA ORIGINAL · PATHFINDER 1E</div><h2>${esc(definition.title)}</h2><p>${esc(definition.description)}</p><p>Al entrar se prepara la guardiana. Después eliges si hablar o combatir.</p><p class="notice">${esc(scopeHint)}</p><form id="pfEncounterEntry"><button class="primary">Entrar con ${esc(own[0].name)}</button></form>${preparedEncounterHelp(definition,own[0])}`);
  $('#pfEncounterEntry').onsubmit=run(async()=>{
   if(token+':'+snapshot.id!==key)throw Error('La campaña ha cambiado.');
   await act('enter_pf_encounter',{encounter:definition.id,encounterVersion:definition.version,character:own[0].id});$('#modal').close();
  });
 });
}

function canExplorePrepared(c){return c.hp>0||(snapshot.state.pfLightExplorationView?.character===c.id&&snapshot.state.pfLightExplorationView?.canExplore===true)}

function renderNextAdventure(panel,s){
 if(!s.nextAdventureView||s.pfEncounter||s.adventureRoute)return;
 if(s.nextAdventureView.kind==='group'){renderSharedNextAdventure(panel,s);return}
 const reason=s.nextAdventureView.reason||(!model.aiConfigured?'El director no está disponible en esta mesa.':'');
 panel.insertAdjacentHTML('beforeend',`<section class="card"><h4>Seguir la aventura aquí</h4><p>La investigación ha terminado. Puedes elegir otro objetivo en este lugar conservando tu personaje, sus heridas y lo descubierto.</p><p id="nextAdventureHint">${esc(reason||'Tú decides qué quieres averiguar. Empezar no cura ni mueve tu personaje.')}</p><button id="nextAdventure" aria-describedby="nextAdventureHint" ${reason?'disabled':''}>Elegir otro objetivo</button><details><summary>Qué cubre la continuación</summary><p>Otra investigación tranquila en el mismo lugar, para un personaje con PG positivos. No prepara viajes, combates, descansos ni recompensas. El juego conserva los capítulos anteriores y no calcula un salto de tiempo.</p></details></section>`);
 $('#nextAdventure').onclick=()=>{
  const campaign=token+':'+snapshot.id,chapter=s.adventureChaptersView?.current||1;
  modal('<h2>¿Qué quieres averiguar aquí?</h2><form id="nextAdventureForm"><label>Tu próximo objetivo<textarea name="premise" required maxlength="2000" rows="4" placeholder="Por ejemplo: quiero averiguar quién dejó el paquete en este lugar."></textarea></label><p>El director preparará otra investigación aquí. Conservas tu ficha, tus heridas y lo descubierto.</p><button class="primary">Continuar aquí</button><p id="nextAdventureProgress" role="status" aria-live="polite"></p></form>');
  $('#nextAdventureForm').onsubmit=run(async e=>{
   if(token+':'+snapshot.id!==campaign||(snapshot.state.adventureChaptersView?.current||1)!==chapter)throw Error('La partida ha cambiado; vuelve a abrir tu próximo objetivo.');
   const button=e.target.querySelector('button');button.disabled=true;$('#nextAdventureProgress').textContent='El director está preparando tu próximo objetivo…';
   try{await act('next_adventure',{premise:e.target.elements.premise.value,worldMemoryContract:'structured-world-memory-1'});$('#modal').close();chooseTab('story')}
   catch(error){$('#nextAdventureProgress').textContent=error.message;throw error}
   finally{button.disabled=false}
  });
 };
}

function renderSharedNextAdventure(panel,s){
 const view=s.nextAdventureView,proposal=view.proposal,mine=proposal?.author===snapshot.me.id;
 const reason=view.reason||proposal?.reason||view.proposalReason||'';
 const hint=reason||(proposal?(mine?'Tu propuesta espera la decisión del otro propietario.':'Revisa el objetivo. Aceptar y continuar pide al director la siguiente investigación aquí.'):'Cada propietario elige por su personaje. Proponer no llama al director.');
 const needsDirector=!model.aiConfigured?'El director no está disponible. Podéis guardar una propuesta y continuar cuando esté conectado.':'';
 panel.insertAdjacentHTML('beforeend',`<section class="card" id="sharedNextAdventure"><h4>Elegir juntos el siguiente objetivo</h4>${proposal?`<p>${esc(proposal.authorName)} propone:</p><blockquote>${esc(proposal.premise)}</blockquote>`:'<p>La investigación está resuelta. Uno propone qué averiguar aquí y el otro decide si continúa.</p>'}<p id="sharedGoalHint" role="status" aria-live="polite" tabindex="-1">${esc(hint)}</p>${needsDirector?`<p id="sharedDirectorHint">${esc(needsDirector)}</p>`:''}<div class="toolbar"><button id="proposeAdventureGoal" aria-describedby="sharedGoalHint" ${!view.canPropose?'disabled':''}>${proposal?(mine?'Cambiar mi propuesta':'Proponer otro objetivo'):'Proponer un objetivo'}</button>${proposal&&!mine&&view.canPropose?`<button class="primary" id="acceptAdventureGoal" aria-describedby="sharedGoalHint${needsDirector?' sharedDirectorHint':''}" ${!proposal.canAccept||!model.aiConfigured?'disabled':''}>Aceptar y continuar</button>`:''}</div><details><summary>Qué cubre la continuación</summary><p>Dos propietarios con una ficha lista cada uno. Otra investigación tranquila en el mismo lugar; conserva las fichas y los capítulos anteriores. No aplica viajes, curación, descansos, recompensas ni un salto de tiempo.</p></details></section>`);
 const campaign=token+':'+snapshot.id,chapter=s.adventureChaptersView?.current||1;
 $('#proposeAdventureGoal').onclick=()=>{
  const previous=proposal?.id||null;
  modal('<h2>¿Qué propones averiguar juntos?</h2><form id="sharedGoalForm"><label>Objetivo que propones<textarea name="premise" required maxlength="2000" rows="4"></textarea></label><p>El otro propietario podrá aceptarlo o proponer una alternativa. Guardar esta propuesta no llama al director.</p><button class="primary">Guardar mi propuesta</button><p id="sharedGoalProgress" role="status" aria-live="polite"></p></form>');
  $('#sharedGoalForm [name=premise]').value=proposal?.premise||'';
  $('#sharedGoalForm').onsubmit=run(async e=>{
   if(token+':'+snapshot.id!==campaign||(snapshot.state.adventureChaptersView?.current||1)!==chapter||(snapshot.state.nextAdventureView?.proposal?.id||null)!==previous)throw Error('La propuesta ha cambiado. Revisa el objetivo del grupo antes de enviar.');
   const button=e.target.querySelector('button');button.disabled=true;
   try{await act('propose_adventure_goal',{premise:e.target.elements.premise.value});$('#modal').close();chooseTab('story')}
   catch(error){$('#sharedGoalProgress').textContent=error.message;throw error}
   finally{button.disabled=false}
  });
 };
 if($('#acceptAdventureGoal'))$('#acceptAdventureGoal').onclick=run(async()=>{
  if(token+':'+snapshot.id!==campaign||(snapshot.state.adventureChaptersView?.current||1)!==chapter||snapshot.state.nextAdventureView?.proposal?.id!==proposal.id)throw Error('La propuesta ha cambiado. Revisa el objetivo antes de aceptarlo.');
  const button=$('#acceptAdventureGoal');button.disabled=true;$('#sharedGoalHint').textContent='El director está preparando el siguiente objetivo acordado…';
  try{await act('next_adventure',{premise:proposal.premise,proposalId:proposal.id,worldMemoryContract:'structured-world-memory-1'});chooseTab('story')}
  finally{if(button.isConnected)button.disabled=!model.aiConfigured||!snapshot.state.nextAdventureView?.proposal?.canAccept}
 });
}

function renderInvestigation(){
 const s=snapshot.state, view=s.adventureModuleView, panel=$('#investigationPanel');
 panel.hidden=!view;
 if(!view){panel.innerHTML='';return}
 const available=s.characters.filter(c=>!c.enemy&&c.owner===snapshot.me.id&&canExplorePrepared(c)&&!c.conditions?.trim()&&c.skillTotals?.some(v=>v.name==='Percepción'));
 const linkedPatient=s.pfContinuation?s.characters.find(c=>c.id===s.pfEncounter.npc):null;
 const linkedLimit=linkedPatient&&((linkedPatient.hp<0&&linkedPatient.hp>-linkedPatient.abilities[2]&&!(s.pfNpcRecoveryView?.canContinue||s.pfLightExplorationView?.canExplore))||linkedPatient.conditions?.trim());
 const pending=s.pending.some(p=>p.investigation),disabled=!available.length||s.board.active||pending||!!linkedLimit;
 panel.innerHTML=`<div class="eyebrow">INVESTIGACIÓN</div><h3>${esc(view.title)}</h3>${view.completed?`<p class="notice">${esc(view.conclusion)}</p>`:`<form id="investigationForm">${available.length===1?`<p class="acting-character">Con <strong>${esc(available[0].name)}</strong></p>`:''}<label ${available.length===1?'hidden':''}>Personaje<select name="character" aria-describedby="investigationHelp">${available.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></label><label>Qué investigas<select name="opportunity" aria-describedby="investigationHelp">${view.opportunities.map(v=>`<option value="${esc(v.id)}">${esc(v.label)}</option>`).join('')}</select></label><div class="toolbar"><button class="primary" value="roll" aria-describedby="investigationHelp" ${disabled?'disabled':''} aria-label="Buscar · tirar d20">Buscar</button><button value="take10" aria-describedby="investigationHelp" ${disabled?'disabled':''}>Elegir 10</button><button value="take20" aria-describedby="investigationHelp" ${disabled?'disabled':''} aria-label="Buscar a fondo · elegir 20">Buscar a fondo</button></div><small id="investigationHelp" role="status" aria-live="polite">${linkedLimit?'La guardiana necesita resolver su estado antes de continuar investigando.':s.board.active?'Las investigaciones automáticas solo están disponibles fuera de combate.':pending?'Hay una prueba de investigación pendiente.':!available.length?'No tienes un personaje disponible para buscar. Cada jugador decide qué investiga su personaje; crea tu ficha o espera su búsqueda.':'Entorno tranquilo y sin riesgos de fallo. Elegir 20 invierte veinte veces el esfuerzo; la duración exacta aún no se calcula.'}</small></form>`}${view.discoveries.length?`<h4>Pistas confirmadas</h4>${view.discoveries.map(v=>`<p>${esc(v.text)}</p>`).join('')}`:''}<details class="scene-recap"><summary>Recordar la situación inicial</summary><p>${esc(view.description)}</p></details><small>${s.pfLightExplorationView?.canExplore?'Estás incapacitado: estas búsquedas y caminar sin prisa no cuestan PG. No realizas acciones fatigosas. ':''}${view.searchActions} acciones de búsqueda registradas. Puedes seguir hablando y declarando acciones libremente en la conversación.</small>`;
 if($('#investigationForm'))$('#investigationForm').onsubmit=run(async e=>{
  const data={...values(e.target),method:e.submitter?.value||'roll'};
  await act('investigate',data);
 });
 if(view.completed)renderNextAdventure(panel,s);
 const route=s.adventureRouteView;
 if(route){
  const blocked=!available.length||s.board.active||s.pending.length>0||s.characters.filter(c=>!c.enemy).length!==1||!!linkedLimit;
  panel.insertAdjacentHTML('beforeend',`<div class="card"><div class="eyebrow">RUTA INDIVIDUAL</div><h4>${esc(route.title)}</h4><p>${route.completed?'Ruta completada. Tú decides qué hace tu personaje después.':'Elige dónde continuar. Los hallazgos se conservan al regresar.'}</p><div class="toolbar">${route.exits.map(e=>`<button data-route-exit="${esc(e.id)}" ${blocked?'disabled':''}>${esc(e.label)}${s.pfLightExplorationView?.canExplore?' · caminando':''}</button>`).join('')}</div><small>${linkedLimit?'La guardiana necesita resolver su estado antes de cambiar de lugar. ':!available.length?'No hay un personaje disponible que puedas controlar. ':''}${route.visits} visitas registradas. Cambiar de escena no calcula tiempo ni movimiento táctico; no admite peligros o combate durante el trayecto.</small></div>`);
  $$('[data-route-exit]').forEach(button=>button.onclick=run(()=>act('travel_scene',{exit:button.dataset.routeExit})));
 }
}
