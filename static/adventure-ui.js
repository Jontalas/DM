/* Adventure preparation is an explicit action; rendering and reading stay local. */
function renderAdventure(){
 const s=snapshot.state, host=!!snapshot.me.host, active=!!s.adventure;
 const ready=s.characters.some(c=>!c.enemy&&c.creation&&!c.creation.manualOverride&&c.hp>0&&!c.conditions?.trim());
 const entry=$('#adventureEntry');
 entry.hidden=active;
 entry.innerHTML=active?'':`<div class="card"><div class="eyebrow">LA PRIMERA PÁGINA</div><h3>El mundo espera a tu personaje</h3><p>${host?'La IA preparará un comienzo, personajes y secretos a partir de la premisa de tu campaña. Después, tú decides cómo actuar.':'El anfitrión puede iniciar la aventura cuando haya un personaje listo.'}</p>${host?`<button id="beginAdventure" class="primary" ${!ready||!model.aiConfigured||s.board.active?'disabled':''}>Iniciar aventura con IA</button><small>${!ready?'Crea primero un personaje con el asistente.':!model.aiConfigured?'Falta configurar el director de IA.':s.board.active?'Finaliza el combate para comenzar.':'El comienzo se guarda para continuar en otra sesión.'}</small>`:''}</div>`;
 if($('#beginAdventure'))$('#beginAdventure').onclick=()=>{
  modal(`<div class="eyebrow">UN NUEVO COMIENZO</div><h2>¿Qué historia te apetece vivir?</h2><form id="adventureForm"><label>Aventura<select name="source"><option value="generated">Crear a partir de mi premisa</option><option value="example">La carta perdida · investigación breve</option><option value="import">Usar una aventura JSON compatible</option></select></label><label id="premiseField">Premisa<textarea name="premise" required maxlength="2000" rows="4">${esc(s.goal)}</textarea></label><label id="moduleFileField" hidden>Archivo de aventura<input type="file" name="moduleFile" accept=".json,application/json"><small>Formato cronicas-adventure-1, una escena tranquila con Percepción; hasta 64 KiB. Usa contenido que tengas derecho a utilizar.</small></label><p>El director respetará el tono y los límites de tu campaña. Preparará la aventura sin decidir las acciones de tu personaje.</p><button class="primary">Preparar y comenzar</button><p id="adventureProgress" role="status" aria-live="polite"></p><small>Se utiliza la IA configurada. El combate y las reglas aún tienen cobertura limitada.</small></form>`);
  $('#adventureForm [name=source]').onchange=e=>{
   $('#premiseField').hidden=e.target.value!=='generated';
   $('#adventureForm [name=premise]').required=e.target.value==='generated';
   $('#moduleFileField').hidden=e.target.value!=='import';
   $('#adventureForm [name=moduleFile]').required=e.target.value==='import';
  };
  $('#adventureForm').onsubmit=run(async e=>{
   const form=e.target,button=form.querySelector('button');button.disabled=true;
   $('#adventureProgress').textContent='El director está preparando la aventura…';
   try{
    const data={premise:form.elements.premise.value,structured:form.elements.source.value==='generated'};
    if(form.elements.source.value==='example')data.moduleId='la-carta-perdida';
    if(form.elements.source.value==='import'){
     const file=form.elements.moduleFile.files[0];if(!file||file.size>64000)throw Error('Elige un archivo JSON de hasta 64 KiB.');
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
 $('#adventureRevision').textContent=active?`Memoria narrativa del director · revisión ${s.adventure.revision}. Las tiradas y sus consecuencias se consultan en el registro.`:'';
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
}

function renderInvestigation(){
 const s=snapshot.state, view=s.adventureModuleView, panel=$('#investigationPanel');
 panel.hidden=!view;
 if(!view){panel.innerHTML='';return}
 const available=s.characters.filter(c=>!c.enemy&&(snapshot.me.host||c.owner===snapshot.me.id)&&c.hp>0&&!c.conditions?.trim()&&c.skillTotals?.some(v=>v.name==='Percepción'));
 const pending=s.pending.some(p=>p.investigation),disabled=!available.length||s.board.active||pending;
 panel.innerHTML=`<div class="eyebrow">INVESTIGACIÓN</div><h3>${esc(view.title)}</h3><p>${esc(view.description)}</p>${view.completed?`<p class="notice">${esc(view.conclusion)}</p>`:`<form id="investigationForm"><label>Personaje<select name="character">${available.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></label><label>Qué investigas<select name="opportunity">${view.opportunities.map(v=>`<option value="${esc(v.id)}">${esc(v.label)}</option>`).join('')}</select></label><div class="toolbar"><button class="primary" value="roll" ${disabled?'disabled':''}>Buscar · tirar d20</button><button value="take10" ${disabled?'disabled':''}>Elegir 10</button><button value="take20" ${disabled?'disabled':''}>Buscar a fondo · elegir 20</button></div><small>${s.board.active?'Las investigaciones automáticas solo están disponibles fuera de combate.':pending?'Hay una prueba de investigación pendiente.':'Entorno tranquilo y sin riesgos de fallo. Elegir 20 invierte veinte veces el esfuerzo; la duración exacta aún no se calcula.'}</small></form>`}${view.discoveries.length?`<h4>Pistas confirmadas</h4>${view.discoveries.map(v=>`<p>${esc(v.text)}</p>`).join('')}`:''}<small>${view.searchActions} acciones de búsqueda registradas. Puedes seguir hablando y declarando acciones libremente en la conversación.</small>`;
 if($('#investigationForm'))$('#investigationForm').onsubmit=run(async e=>{
  const data={...values(e.target),method:e.submitter?.value||'roll'};
  await act('investigate',data);
 });
}
