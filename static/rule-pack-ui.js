/* One workspace for imported rule data. No game names or mechanical formulas. */
window.RulePackUI=(()=>{
 const drafts=new Map();
 const scope=()=>snapshot.id+':'+snapshot.me.id;
 const shown=value=>typeof value==='boolean'?(value?'Sí':'No'):String(value??'');
 const list=items=>items.map(item=>`<li>${esc(item)}</li>`).join('');
 function historyEntry(m,doc){
  if(m.kind==='system')return `<p>${esc(m.text)}</p>`;
  if(m.kind==='pack-talk'||m.kind==='pack-director')return `<article class="pack-story-message"><h4>${esc(m.speaker)}${m.mode==='ooc'?' · Fuera de personaje':''}</h4><p>${esc(m.text)}</p>${m.limitation?`<p class="notice">Límite del motor: ${esc(m.limitation)}</p>`:''}</article>`;
  return `<article><h4>${esc(m.speaker)} · ${esc(doc.actions[m.action]?.label||m.action)}</h4>${Object.entries(m.trace.rolls).filter(([,r])=>r.rolled).map(([id,r])=>`<p>${esc(id)}: ${esc(r.values.join(', '))} → ${r.total} · ${r.origin==='physical'?'dados físicos':'servidor'}</p>`).join('')}${Object.entries(m.trace.changes).map(([id,v])=>`<p>${esc(doc.fields[id]?.label||id)}: ${esc(shown(v.before))} → ${esc(shown(v.after))}</p>`).join('')}${m.trace.triggers.map(t=>`<p>Consecuencia automática: ${esc(doc.triggers[t.id]?.label||t.id)}</p>`).join('')}</article>`;
 }
 function followStory(key){if(!$('#app').hidden&&scope()===key)($('#packStoryResolve')||$('#packStoryContinue')||$('#packStoryTalk'))?.scrollIntoView({block:'nearest'});}
 function renderAdventure(root,doc){
  if(snapshot.state.package?.policy!=='provided-rules')return;
  const key=scope(),state=snapshot.state,me=snapshot.me,memory=state.narrativeView,own=state.characters.filter(c=>c.owner===me.id);
  const history=root.querySelector('.pack-history');history.querySelector('h3').textContent=memory?'Aventura y resoluciones':'Registro de resoluciones';
  const controls=document.createElement('div');controls.id='packAdventure';history.append(controls);
  if(!memory){
   controls.innerHTML=me.host&&own.length?`<h3>Jugar esta aventura</h3><p>El director abre una situación a partir del objetivo de la campaña. Solo se resuelven las mecánicas disponibles en el paquete.</p><form id="packStoryStart"><label>Tu personaje<select name="character">${own.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></label><button class="primary">Iniciar aventura con IA</button></form>`:'<p>Crea tu personaje para entrar en la aventura. El anfitrión inicia la escena compartida.</p>';
   if($('#packStoryStart'))$('#packStoryStart').onsubmit=run(async e=>{sameCampaign(key);await act('start_pack_adventure',{character:e.target.elements.character.value});followStory(key);});
   return;
  }
  $$('[data-pack-action]').forEach(b=>b.remove());
  const pending=memory.pending,continuation=memory.continuation;
  controls.innerHTML=`<details><summary>Recordar lo ocurrido</summary><p>${esc(memory.summary)}</p></details>${pending?`<section class="pack-request"><h3>${esc(doc.actions[pending.action].label)}</h3><p>${esc(state.characters.find(c=>c.id===pending.character)?.name)} · ${esc(pending.reason)}</p><div id="packRequestBody"></div></section>`:''}${continuation?'<p>La ficha y los dados ya están guardados. Falta narrar ese resultado.</p><button id="packStoryContinue" class="primary">Continuar relato con IA</button>':''}${own.length?`<form id="packStoryTalk"><h3>Tu intervención</h3><label>Personaje<select name="character">${own.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></label><label>Intervención<select name="mode"><option value="action">Declarar acción</option><option value="dialogue">Hablar en personaje</option><option value="ooc">Fuera de personaje · sin IA</option></select></label><label>¿Qué haces o dices?<textarea name="text" maxlength="4000" rows="3" required></textarea></label><button class="primary">Enviar intervención</button></form>`:'<p>Necesitas un personaje propio para intervenir.</p>'}`;
  if(pending){
   const actor=state.characters.find(c=>c.id===pending.character),action=doc.actions[pending.action],body=$('#packRequestBody');
   if(actor.owner!==me.id)body.innerHTML='<p>La decisión y los dados corresponden a su jugador.</p>';
   else{
    const draftKey=key+':request:'+pending.id,saved=drafts.get(draftKey)||{inputs:pending.inputs,physical:{}};
    body.innerHTML=`<form id="packStoryResolve">${Object.entries(action.inputs).map(([id,spec],i)=>`<label>${esc(spec.label)}${input(spec,i,saved.inputs[id])}</label>`).join('')}${action.rolls.length?`<details><summary>Usar dados físicos, opcional</summary>${action.rolls.map((r,i)=>`<label>${esc(r.id)}<input name="dice${i}" value="${esc(saved.physical[r.id]||'')}" placeholder="3, 4" inputmode="numeric"></label>`).join('')}</details>`:''}<p>El motor comprobará la acción y aplicará sus consecuencias.</p><button class="primary">${action.rolls.length?'Tirar y resolver':'Resolver acción'}</button><button type="button" id="packStoryCancel">Retirar acción</button></form>`;
    body.insertAdjacentHTML('afterbegin',`<p>Previsión con las opciones solicitadas: ${pending.rolls.length?pending.rolls.map(r=>`${r.count}d${r.sides}${r.keep!==r.count?` · conservar ${r.keep}`:''}${action.rolls.find(spec=>spec.id===r.id)?.when!==undefined?' (si corresponde)':''}`).map(esc).join(', '):'sin dados'}. ${Object.keys(action.inputs).length?'Las decisiones que cambies pueden modificar los dados; el motor los comprobará.':''}</p>`);
    const form=$('#packStoryResolve');
    function remember(){drafts.set(draftKey,{inputs:formValues(form,action),physical:Object.fromEntries(action.rolls.map((r,i)=>[r.id,form.elements['dice'+i].value]))});}
    form.oninput=remember;form.onchange=remember;
    form.onsubmit=run(async()=>{
     sameCampaign(key);remember();const physical=Object.fromEntries(action.rolls.flatMap((r,i)=>{
      const raw=form.elements['dice'+i].value.trim();if(!raw)return [];
      if(!/^\d+(\s*,\s*\d+)*$/.test(raw))throw Error('Escribe dados enteros separados por comas.');return [[r.id,raw.split(',').map(Number)]];
     }));
     await act('resolve_pack_request',{request:pending.id,inputs:formValues(form,action),...(Object.keys(physical).length?{physical}:{})});
     drafts.delete(draftKey);sameCampaign(key);followStory(key);
     if(snapshot.state.narrativeView?.continuation?.character===actor.id)await act('continue_pack_adventure');
     followStory(key);
    });
    $('#packStoryCancel').onclick=run(async()=>{sameCampaign(key);await act('cancel_pack_request',{request:pending.id});drafts.delete(draftKey);followStory(key);});
   }
  }
  if($('#packStoryContinue')){
   const actor=state.characters.find(c=>c.id===continuation.character);
   $('#packStoryContinue').disabled=actor?.owner!==me.id;
   $('#packStoryContinue').onclick=run(async()=>{sameCampaign(key);await act('continue_pack_adventure');followStory(key);});
  }
  if($('#packStoryTalk')){
   const form=$('#packStoryTalk'),draftKey=key+':story-message',saved=drafts.get(draftKey);
   if(saved){if(own.some(c=>c.id===saved.character))form.elements.character.value=saved.character;form.elements.mode.value=saved.mode;form.elements.text.value=saved.text;}
   form.oninput=()=>drafts.set(draftKey,{character:form.elements.character.value,mode:form.elements.mode.value,text:form.elements.text.value});form.onchange=form.oninput;
   form.onsubmit=run(async()=>{sameCampaign(key);await act('talk_pack_adventure',{character:form.elements.character.value,mode:form.elements.mode.value,text:form.elements.text.value});drafts.delete(draftKey);if($('#packStoryTalk'))$('#packStoryTalk').elements.text.value='';followStory(key);});
  }
 }
 function description(view){
  return `<h3>${esc(view.name)}</h3><p>${esc(view.edition)} · versión ${esc(view.version)}</p><p class="notice">Estructura válida. Correspondencia con el manual sin verificar.</p><h4>Incluido según el paquete</h4><ul>${list(view.coverage.implemented)}</ul><h4>Pendiente según el paquete</h4><ul>${list(view.coverage.pending)}</ul><details><summary>Fuentes y atribución</summary>${view.sources.map(s=>`<p><strong>${esc(s.title)}</strong><br>${esc(s.edition)} · ${esc(s.locator)}</p>`).join('')}<p>${esc(view.license.id)} · ${esc(view.license.attribution)}</p><small>La referencia declarada no acredita por sí sola que la interpretación sea correcta.</small></details>`;
 }
 function sameCampaign(key){if($('#app').hidden||!token||scope()!==key||snapshot.state.ruleset!=='rule-pack')throw Error('La campaña ha cambiado. Abre de nuevo el paquete en su sala.');}
 function review(raw,view,preparation){
  const key=scope();
  modal(`<div class="eyebrow">REVISAR PAQUETE DE REGLAS</div>${description(view)}<p>${view.fields} campos · ${view.actions} acciones · ${view.tables} tablas</p><p>El borrador se puede consultar, pero no ejecutar. Usar sus definiciones no certifica fidelidad al manual.</p><form id="packInstall"><label class="check"><input type="checkbox" name="use"> Usar las definiciones aportadas, con su cobertura y límites declarados</label><button class="primary">Guardar paquete</button></form>`);
  $('#packInstall').onsubmit=run(async e=>{
   sameCampaign(key);const policy=e.target.elements.use.checked?'provided-rules':'draft';
   if(preparation)await act('install_prepared_rule_pack',{preparation,policy});
   else await act('install_rule_pack',{package:raw,policy});
   $('#modal').close();
  });
 }
 async function readPackage(file){
  if(!file)return;
  if(file.size>256000)throw Error('El paquete supera el límite de 256.000 bytes.');
  const key=scope(),raw=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());
  const view=await api('/api/rule-pack/inspect',{package:raw});sameCampaign(key);review(raw,view);
 }
 function input(spec,index,value){
  const attrs=`name="input${index}"`;
  if(spec.options)return `<select ${attrs}>${spec.options.map(v=>`<option value="${esc(v)}" ${String(value)===String(v)?'selected':''}>${esc(shown(v))}</option>`).join('')}</select>`;
  if(spec.type==='boolean')return `<select ${attrs}><option value="false" ${value!==true?'selected':''}>No</option><option value="true" ${value===true?'selected':''}>Sí</option></select>`;
  return `<input ${attrs} type="${spec.type==='integer'?'number':'text'}" value="${esc(value??spec.default??'')}" ${spec.type==='integer'?`step="1" ${spec.min!==undefined?`min="${spec.min}"`:''} ${spec.max!==undefined?`max="${spec.max}"`:''}`:`maxlength="${spec.maxLength??4000}"`} required>`;
 }
 function formValues(form,action){
  return Object.fromEntries(Object.entries(action.inputs).map(([id,spec],i)=>{
   const value=form.elements['input'+i].value;
   return [id,spec.type==='integer'?Number(value):spec.type==='boolean'?value==='true':value];
  }));
 }
 function openAction(characterId,actionId){
  const key=scope(),c=snapshot.state.characters.find(v=>v.id===characterId),doc=snapshot.state.package.document,action=doc.actions[actionId];
  if(!c||!action)return;
  const draftKey=key+':'+c.id+':'+actionId,saved=drafts.get(draftKey)||{inputs:{},physical:{}};
  modal(`<div class="eyebrow">ACCIÓN · ${esc(c.name)}</div><h2>${esc(action.label)}</h2><p>El servidor comprueba requisitos y calcula las consecuencias definidas por el paquete.</p><form id="packAction">${Object.entries(action.inputs).map(([id,spec],i)=>`<label>${esc(spec.label)}${input(spec,i,saved.inputs[id]??spec.default)}</label>`).join('')}${action.rolls.length?`<details><summary>Usar dados físicos, opcional</summary><p>Deja cada campo vacío para tirar en el servidor. Si lo rellenas, escribe todos sus dados separados por comas.</p>${action.rolls.map((r,i)=>`<label>${esc(r.id)}<input name="dice${i}" value="${esc(saved.physical[r.id]||'')}" placeholder="Por ejemplo: 3, 4" inputmode="numeric"></label>`).join('')}</details>`:''}<button class="primary">Resolver ${esc(action.label)}</button></form>`);
  const form=$('#packAction');
  function remember(){drafts.set(draftKey,{inputs:formValues(form,action),physical:Object.fromEntries(action.rolls.map((r,i)=>[r.id,form.elements['dice'+i].value]))});}
  form.oninput=remember;form.onchange=remember;
  form.onsubmit=run(async()=>{
   sameCampaign(key);remember();
   const physical=Object.fromEntries(action.rolls.flatMap((r,i)=>{
    const raw=form.elements['dice'+i].value.trim();if(!raw)return [];
    if(!/^\d+(\s*,\s*\d+)*$/.test(raw))throw Error('Escribe dados enteros separados por comas.');
    return [[r.id,raw.split(',').map(Number)]];
   }));
   await act('run_pack_action',{character:c.id,action:actionId,inputs:formValues(form,action),...(Object.keys(physical).length?{physical}:{})});
   drafts.delete(draftKey);$('#modal').close();
  });
 }
 function openCharacter(id){
  const c=snapshot.state.characters.find(v=>v.id===id);if(!c)return;
  const doc=snapshot.state.package.document;
  modal(`<div class="eyebrow">FICHA · ${esc(doc.name)}</div><h2>${esc(c.name)}</h2><dl class="pack-fields">${Object.entries(doc.fields).map(([key,spec])=>`<div><dt>${esc(spec.label)}</dt><dd>${esc(shown(c.view.fields[key]))}</dd></div>`).join('')}</dl><small>Valores calculados por el motor. Los cambios se realizan mediante acciones del paquete.</small>`);
  if(c.creation)$('#modalContent').insertAdjacentHTML('beforeend',`<details><summary>Origen de la ficha: elecciones y dados</summary>${Object.entries(c.creation.inputs).map(([id,value])=>`<p>${esc(doc.actions[doc.creation.action].inputs[id]?.label||id)}: ${esc(shown(value))}</p>`).join('')}${Object.entries(c.creation.trace.rolls).filter(([,r])=>r.rolled).map(([id,r])=>`<p>${esc(id)}: ${esc(r.values.join(', '))} → ${r.total} · ${r.origin==='physical'?'dados físicos':'servidor'}</p>`).join('')}</details>`);
 }
 function render(){
  const s=snapshot.state,me=snapshot.me;
  $('#welcome').hidden=true;$('#savedLibraryPanel').hidden=true;$('#app').hidden=false;$('#app > .workspace').hidden=true;
  if($('#systemWorkspace'))$('#systemWorkspace').hidden=true;
  $('#campaignTitle').textContent=snapshot.title;$('#campaignMeta').textContent=s.packageView?s.packageView.name+' · reglas aportadas':'Preparar reglas de la campaña';
  $('#inviteBtn').hidden=!me.host;$('#exportBtn').disabled=!me.host;
  let root=$('#rulePackWorkspace');if(!root){root=document.createElement('section');root.id='rulePackWorkspace';root.className='system-workspace';$('#app').append(root)}root.hidden=false;
  const active=s.package?.policy==='provided-rules',doc=s.package?.document;
  root.innerHTML=`<div class="eyebrow">REGLAS DE LA CAMPAÑA · EXPERIMENTAL</div><h2>${s.packageView?esc(s.packageView.name):'Preparar el reglamento'}</h2><p class="notice">Importación de paquetes JSON. Preparación asistida de fragmentos en pruebas. Director de aventura experimental conectado al paquete. La conversión completa de manuales sigue pendiente.</p><div class="pack-columns"><section><div class="card">${s.packageView?description(s.packageView):'<p>El anfitrión debe cargar un paquete antes de crear fichas. No se aplicarán reglas de otro juego.</p>'}${s.packageView?`<p>${active?'En uso como definiciones aportadas.':'Borrador: ejecución desactivada.'}</p>`:''}${me.host&&!s.characters.length?'<label>Cargar paquete de reglas<input id="packFile" type="file" accept=".json,application/json"></label>':''}${me.host&&s.package&&!active?'<button id="packActivate">Revisar y usar este borrador</button>':''}</div><div id="packCharacters">${s.characters.map(c=>`<article class="card"><h3>${esc(c.name)}</h3><p>${esc(snapshot.players.find(p=>p.id===c.owner)?.name||'Jugador anterior')}</p><button data-pack-character="${esc(c.id)}">Abrir ficha</button><div class="toolbar">${Object.entries(doc.actions).filter(([id,a])=>a.permission==='host'?me.host:c.owner===me.id).map(([id,a])=>`<button data-pack-action="${esc(id)}" data-pack-target="${esc(c.id)}">${esc(a.label)}</button>`).join('')}</div></article>`).join('')}</div>${active?'<form id="packCreate" class="card"><h3>Crear una ficha</h3><p>Se asignan los valores iniciales del paquete. La creación guiada completa depende de reglas todavía pendientes.</p><label>Nombre<input name="name" maxlength="80" required></label><button class="primary">Crear ficha</button></form>':''}${me.host?'<div class="card"><h3>Conservar la campaña</h3><button id="packExport">Guardar copia</button><label>Recuperar copia<input id="packImport" type="file" accept=".json,application/json"></label></div>':''}</section><section class="card pack-history"><h3>Registro de resoluciones</h3>${s.messages.slice(-100).map(m=>historyEntry(m,doc)).join('')||'<p>Las tiradas y consecuencias aparecerán aquí.</p>'}</section></div>`;
  if($('#packFile'))$('#packFile').onchange=run(e=>readPackage(e.target.files[0]));
  if($('#packActivate'))$('#packActivate').onclick=()=>review(s.package.document,s.packageView);
  if($('#packCreate')){
   const nameKey=scope()+':new-name';$('#packCreate').elements.name.value=drafts.get(nameKey)||'';
   const creation=doc.creation?doc.actions[doc.creation.action]:null,choiceKey=scope()+':creation-choices';
   if(creation){
    const saved=drafts.get(choiceKey)||{};
    $('#packCreate h3').textContent='Crear tu personaje';
    $('#packCreate p').textContent=creation.rolls.length?'Elige las opciones de tu personaje. Al confirmar, se tiran los dados y se calcula la ficha según este paquete.':'Elige las opciones de tu personaje. El motor comprobará los requisitos y calculará la ficha.';
    $('#packCreate button').insertAdjacentHTML('beforebegin',`<fieldset><legend>${esc(creation.label)}</legend>${Object.entries(creation.inputs).map(([id,spec],i)=>`<label>${esc(spec.label)}${input(spec,i,saved[id]??spec.default)}</label>`).join('')}</fieldset>`);
    $('#packCreate button').textContent=creation.rolls.length?'Crear personaje y tirar':'Crear personaje';
   }
   $('#packCreate').oninput=e=>{drafts.set(nameKey,e.currentTarget.elements.name.value);if(creation)drafts.set(choiceKey,formValues(e.currentTarget,creation));};
   $('#packCreate').onchange=$('#packCreate').oninput;
   $('#packCreate').onsubmit=run(async e=>{await act('create_pack_sheet',{name:e.target.elements.name.value,...(creation?{inputs:formValues(e.target,creation)}:{})});drafts.delete(nameKey);drafts.delete(choiceKey);if($('#packCreate'))$('#packCreate').elements.name.value='';});
  }
  $$('[data-pack-character]').forEach(b=>b.onclick=()=>openCharacter(b.dataset.packCharacter));
  $$('[data-pack-action]').forEach(b=>{if(b.dataset.packAction===doc?.creation?.action)b.remove();else b.onclick=()=>openAction(b.dataset.packTarget,b.dataset.packAction);});
  if($('#packExport'))$('#packExport').onclick=()=>$('#exportBtn').onclick();
  if($('#packImport'))$('#packImport').onchange=run(async e=>{
   const file=e.target.files[0];if(!file)return;if(file.size>8000000)throw Error('La copia supera el tamaño admitido.');
   if(!confirm('Esta copia sustituye el estado actual y sus fichas pasarán a tu control. Guarda antes una copia para conservarlo.'))return;
   await act('import',{campaign:JSON.parse(await file.text())});
  });
  RulePackAuthoringUI.render(root);
  RulePackComposeUI.render(root);
  renderAdventure(root,doc);
 }
 return {render,openCharacter,review};
})();
