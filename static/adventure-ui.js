/* Adventure preparation is an explicit action; rendering and reading stay local. */
function renderAdventure(){
 const s=snapshot.state, host=!!snapshot.me.host, active=!!s.adventure;
 const ready=s.characters.some(c=>!c.enemy&&c.creation&&!c.creation.manualOverride&&c.hp>0&&!c.conditions?.trim());
 const entry=$('#adventureEntry');
 entry.hidden=active;
 entry.innerHTML=active?'':`<div class="card"><div class="eyebrow">LA PRIMERA PÁGINA</div><h3>El mundo espera a tu personaje</h3><p>${host?'La IA preparará un comienzo, personajes y secretos a partir de la premisa de tu campaña. Después, tú decides cómo actuar.':'El anfitrión puede iniciar la aventura cuando haya un personaje listo.'}</p>${host?`<button id="beginAdventure" class="primary" ${!ready||!model.aiConfigured||s.board.active?'disabled':''}>Iniciar aventura con IA</button><small>${!ready?'Crea primero un personaje con el asistente.':!model.aiConfigured?'El director no está disponible en esta mesa.':s.board.active?'Finaliza el combate para comenzar.':'El comienzo se guarda para continuar en otra sesión.'}</small>`:''}</div>`;
 if($('#beginAdventure'))$('#beginAdventure').onclick=()=>{
  modal(`<div class="eyebrow">UN NUEVO COMIENZO</div><h2>¿Qué historia te apetece vivir?</h2><form id="adventureForm"><label>Aventura<select name="source"><option value="generated">Crear a partir de mi premisa</option><option value="text">Adaptar un texto o documento breve</option><option value="example">La carta perdida · investigación breve</option><option value="route">Los senderos del archivo · ruta individual</option><option value="import">Usar una aventura JSON compatible</option></select></label><label id="premiseField">Premisa<textarea name="premise" required maxlength="2000" rows="4">${esc(s.goal)}</textarea></label><label id="moduleFileField" hidden>Archivo de aventura<input type="file" name="moduleFile" accept=".json,application/json"><small>Una escena cronicas-adventure-1 (64 KiB) o ruta individual cronicas-route-1 (192.000 bytes). Investigaciones tranquilas de Percepción. Usa contenido que tengas derecho a utilizar.</small></label><div id="sourceTextField" hidden><label>Texto de la aventura<textarea name="sourceText" maxlength="12000" rows="6" placeholder="Pega un fragmento de la aventura"></textarea></label><label>Cargar texto desde un archivo<input type="file" name="sourceFile" accept=".txt,.md,text/plain,text/markdown"></label><small>Hasta 12.000 caracteres en UTF-8. Usa contenido que tengas derecho a utilizar. La IA adaptará una sola situación a dos búsquedas de Percepción, sin peligros ni combate; no convierte la aventura completa. El texto se envía al director al comenzar y puede contener secretos. Se conserva la adaptación; guarda tu original aparte.</small></div><p>El director respetará el tono y los límites de tu campaña. Preparará la aventura sin decidir las acciones de tu personaje.</p><button class="primary">Preparar y comenzar</button><p id="adventureProgress" role="status" aria-live="polite"></p><small>Se utiliza la IA configurada. El combate y las reglas aún tienen cobertura limitada.</small></form>`);
  $('#adventureForm [name=source]').onchange=e=>{
   $('#premiseField').hidden=e.target.value!=='generated';
   $('#adventureForm [name=premise]').required=e.target.value==='generated';
   $('#sourceTextField').hidden=e.target.value!=='text';
   $('#adventureForm [name=sourceText]').required=e.target.value==='text';
   $('#moduleFileField').hidden=e.target.value!=='import';
   $('#adventureForm [name=moduleFile]').required=e.target.value==='import';
  };
  $('#adventureForm [name=sourceFile]').onchange=run(async e=>{
   const file=e.target.files[0];if(!file)return;
   if(!/\.(txt|md)$/i.test(file.name)||file.size>48000)throw Error('Elige un archivo .txt o .md UTF-8 de hasta 48.000 bytes.');
   let text;try{text=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer())}catch{throw Error('El archivo debe estar codificado en UTF-8.')}
   if(!text.trim()||[...text].length>12000||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(text))throw Error('El documento debe contener texto legible, entre 1 y 12.000 caracteres.');
   $('#adventureForm [name=sourceText]').value=text;
  });
  $('#adventureForm').onsubmit=run(async e=>{
   const form=e.target,button=form.querySelector('button');button.disabled=true;
   $('#adventureProgress').textContent='El director está preparando la aventura…';
   try{
    const data={premise:form.elements.premise.value,structured:form.elements.source.value==='generated'};
    if(form.elements.source.value==='text'){
     data.sourceText=form.elements.sourceText.value.trim();
     if(!data.sourceText||[...data.sourceText].length>12000)throw Error('Aporta entre 1 y 12.000 caracteres de texto.');
     data.structured=true;
    }
    if(form.elements.source.value==='route')data.moduleId='senderos-del-archivo';
    if(form.elements.source.value==='example')data.moduleId='la-carta-perdida';
    if(form.elements.source.value==='import'){
     const file=form.elements.moduleFile.files[0];if(!file||file.size>192000)throw Error('Elige un archivo JSON de hasta 192.000 bytes.');
     try{data.module=JSON.parse(await file.text())}catch{throw Error('El archivo no contiene JSON válido.')}
    }
    await act('start_adventure',data);$('#modal').close();chooseTab('story');
   }
   catch(error){$('#adventureProgress').textContent=error.message;throw error;}
   finally{button.disabled=false;}
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
 continuation.onclick=run(()=>act('continue_adventure'));
 renderInvestigation();
 renderPreparedPathfinderEncounter();
}

function preparedEncounterHelp(definition,actor){
 const limited=['single-unconscious-player-1','shared-patients-1'].includes(definition.recoveryScope)&&actor?.hp>=0&&actor?.creation?.choices?.armor==='scale';
 return `${limited?'<p class="notice recovery-limit">Si caes inconsciente con tu cota de escamas, la recuperación posterior necesitará una resolución excepcional. El juego conservará tu estado.</p>':''}<details class="encounter-help"><summary>Qué incluye este encuentro</summary><p>${esc(definition.coverage)}</p><p>Una persona juega con su personaje. Luz normal, patio abierto y sin sorpresa. La guardiana tiene su ficha preparada.</p><p>Su disposición a negociar pertenece a esta escena; otras conversaciones pueden necesitar una prueba de Diplomacia.</p></details>`;
}

function preparedEncounterHealthDescription(record,actor,npc){
 if(record.phase!=='defeated')return '';
 if(characterIsConscious(actor)){
  if(record.definition.recoveryScope==='shared-patients-1'&&npc&&!characterIsConscious(npc))return npc.hp<=-npc.abilities[2]?'Has recuperado la consciencia. La guardiana ha muerto; tú decides qué haces a continuación.':'Has recuperado la consciencia. La guardiana sigue inconsciente; tú decides qué haces a continuación.';
  return ['single-unconscious-player-1','shared-patients-1'].includes(record.definition.recoveryScope)?'Has recuperado la consciencia. La guardiana te permite retirarte; tú decides qué haces a continuación.':'Estás consciente. Consulta tus heridas en la ficha; tú decides qué haces a continuación.';
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
  const description=preparedEncounterHealthDescription(record,actor,patient)|| (record.phase==='offered'?definition.description:record.phase==='agreement'?definition.agreement:record.phase==='resolved'?`Desenlace registrado: ${record.outcome.status==='stable'?'adversario inconsciente y estable':'muerte del adversario'}, con ${record.outcome.hp} PG. No se recuperan PG ni se mueve tu ficha. Tú decides qué haces después.`:record.phase==='defeated'?`Desenlace registrado del personaje: ${record.outcome.status==='dead'?'muerto':'inconsciente y estable'}, con ${record.outcome.hp} PG. Se conservan las heridas. Consulta el estado actual en tu ficha.`:'El combate está iniciado. La iniciativa, los ataques y el estado de los participantes se consultan en el tablero y el registro.');
  entry.innerHTML=`<section class="card"><div class="eyebrow">ENCUENTRO PREPARADO · EXPERIMENTAL</div><h3>${esc(definition.title)}</h3><p>${esc(description)}</p>${record.phase==='offered'?`<p><strong>${mine?'Decide cómo responder.':'El propietario del personaje decide cómo responder.'}</strong></p><div class="toolbar"><button id="pfEncounterParley" ${mine?'':'disabled'}>Proponer el paso sin combatir</button><button id="pfEncounterCombat" ${mine?'':'disabled'}>Entrar en combate</button></div>`:''}${actor.hp<0&&characterIsConscious(actor)?'<p class="notice">Ahora estás consciente, con PG negativos. Puedes moverte o realizar una acción estándar, pero no ambas; una acción fatigosa cuesta 1 PG y puede hacerte caer de nuevo. No has recuperado PG.</p>':''}${record.recoveryOutcome?`<p>Tiempo transcurrido: ${record.recoveryOutcome.hours} ${record.recoveryOutcome.hours===1?'hora':'horas'}. Consulta las tiradas en el registro.</p>`:''}<div id="pfEncounterAid"></div>${preparedEncounterHelp(definition,actor)}</section>`;
  if(definition.continuation&&['agreement','resolved','defeated'].includes(record.phase)){
   const ready=mine&&!s.board.active&&actor.hp>0&&(patient.hp>=0||patient.hp<=-patient.abilities[2]);
   const hint=actor.hp<=0?'Tu personaje necesita recuperarse antes de investigar.':patient.hp<0&&patient.hp>-patient.abilities[2]?'La guardiana sigue necesitando seguimiento de sus heridas.':'Puedes examinar el registro del banco sin abandonar el patio. No recuperas PG al continuar.';
   entry.querySelector('.card').insertAdjacentHTML('beforeend',`<p id="pfContinueHint">${esc(hint)}</p><button id="pfContinueScene" class="primary" aria-describedby="pfContinueHint" ${ready?'':'disabled'}>Investigar el registro del patio</button>`);
   $('#pfContinueScene').onclick=run(()=>act('continue_pf_encounter'));
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
 entry.insertAdjacentHTML('beforeend','<section class="card"><h3>Un encuentro preparado</h3><p>Entrar con tu personaje y un adversario del catálogo, sin escribir estadísticas. Encuentro experimental; el descanso curativo y la siguiente escena siguen pendientes.</p><button id="beginPreparedEncounter">Consultar El patio del peaje</button></section>');
 $('#beginPreparedEncounter').onclick=run(async()=>{
  const key=token+':'+snapshot.id,{encounters}=await api('/api/pf-encounters'),definition=encounters[0];
  if(token+':'+snapshot.id!==key)throw Error('La campaña ha cambiado; vuelve a abrir el encuentro.');
  modal(`<div class="eyebrow">ESCENA ORIGINAL · PATHFINDER 1E</div><h2>${esc(definition.title)}</h2><p>${esc(definition.description)}</p><p>Al entrar se prepara la guardiana. Después eliges si hablar o combatir.</p><p class="notice">Encuentro básico experimental. El descanso curativo y la siguiente escena siguen en desarrollo.</p><form id="pfEncounterEntry"><button class="primary">Entrar con ${esc(own[0].name)}</button></form>${preparedEncounterHelp(definition,own[0])}`);
  $('#pfEncounterEntry').onsubmit=run(async()=>{
   if(token+':'+snapshot.id!==key)throw Error('La campaña ha cambiado.');
   await act('enter_pf_encounter',{encounter:definition.id,encounterVersion:definition.version,character:own[0].id});$('#modal').close();
  });
 });
}

function renderInvestigation(){
 const s=snapshot.state, view=s.adventureModuleView, panel=$('#investigationPanel');
 panel.hidden=!view;
 if(!view){panel.innerHTML='';return}
 const available=s.characters.filter(c=>!c.enemy&&(snapshot.me.host||c.owner===snapshot.me.id)&&c.hp>0&&!c.conditions?.trim()&&c.skillTotals?.some(v=>v.name==='Percepción'));
 const linkedPatient=s.pfContinuation?s.characters.find(c=>c.id===s.pfEncounter.npc):null;
 const linkedLimit=linkedPatient&&((linkedPatient.hp<0&&linkedPatient.hp>-linkedPatient.abilities[2])||linkedPatient.conditions?.trim());
 const pending=s.pending.some(p=>p.investigation),disabled=!available.length||s.board.active||pending||!!linkedLimit;
 panel.innerHTML=`<div class="eyebrow">INVESTIGACIÓN</div><h3>${esc(view.title)}</h3><p>${esc(view.description)}</p>${view.completed?`<p class="notice">${esc(view.conclusion)}</p>`:`<form id="investigationForm"><label>Personaje<select name="character">${available.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></label><label>Qué investigas<select name="opportunity">${view.opportunities.map(v=>`<option value="${esc(v.id)}">${esc(v.label)}</option>`).join('')}</select></label><div class="toolbar"><button class="primary" value="roll" ${disabled?'disabled':''}>Buscar · tirar d20</button><button value="take10" ${disabled?'disabled':''}>Elegir 10</button><button value="take20" ${disabled?'disabled':''}>Buscar a fondo · elegir 20</button></div><small>${linkedLimit?'La guardiana necesita resolver su estado antes de continuar investigando.':s.board.active?'Las investigaciones automáticas solo están disponibles fuera de combate.':pending?'Hay una prueba de investigación pendiente.':'Entorno tranquilo y sin riesgos de fallo. Elegir 20 invierte veinte veces el esfuerzo; la duración exacta aún no se calcula.'}</small></form>`}${view.discoveries.length?`<h4>Pistas confirmadas</h4>${view.discoveries.map(v=>`<p>${esc(v.text)}</p>`).join('')}`:''}<small>${view.searchActions} acciones de búsqueda registradas. Puedes seguir hablando y declarando acciones libremente en la conversación.</small>`;
 if($('#investigationForm'))$('#investigationForm').onsubmit=run(async e=>{
  const data={...values(e.target),method:e.submitter?.value||'roll'};
  await act('investigate',data);
 });
 const route=s.adventureRouteView;
 if(route){
  const blocked=!available.length||s.board.active||s.pending.length>0||s.characters.filter(c=>!c.enemy).length!==1;
  panel.insertAdjacentHTML('beforeend',`<div class="card"><div class="eyebrow">RUTA INDIVIDUAL</div><h4>${esc(route.title)}</h4><p>${route.completed?'Ruta completada. Tú decides qué hace tu personaje después.':'Elige dónde continuar. Los hallazgos se conservan al regresar.'}</p><div class="toolbar">${route.exits.map(e=>`<button data-route-exit="${esc(e.id)}" ${blocked?'disabled':''}>${esc(e.label)}</button>`).join('')}</div><small>${route.visits} visitas registradas. Cambiar de escena no calcula tiempo ni movimiento táctico; no admite peligros o combate durante el trayecto.</small></div>`);
  $$('[data-route-exit]').forEach(button=>button.onclick=run(()=>act('travel_scene',{exit:button.dataset.routeExit})));
 }
}
