/* One workspace for imported rule data. No game names or mechanical formulas. */
window.RulePackUI=(()=>{
 const drafts=new Map();
 const scope=()=>snapshot.id+':'+snapshot.me.id;
 const shown=value=>typeof value==='boolean'?(value?'Sí':'No'):String(value??'');
 const list=items=>items.map(item=>`<li>${esc(item)}</li>`).join('');
 const creationSteps=doc=>doc?.creation?.steps||(doc?.creation?.action?[doc.creation.action]:[]);
 const reservedCreation=doc=>new Set([...creationSteps(doc),...Object.values(doc?.creationProfiles||{}).flatMap(profile=>profile.steps)]);
 function historyEntry(m,doc){
  if(m.kind==='system')return `<p>${esc(m.text)}</p>`;
  if(m.kind==='pack-talk'||m.kind==='pack-director')return `<article class="pack-story-message"><h4>${esc(m.speaker)}${m.mode==='ooc'?' · Fuera de personaje':''}</h4><p>${esc(m.text)}</p>${m.limitation?`<p class="notice">Límite del motor: ${esc(m.limitation)}</p>`:''}</article>`;
  let resultContext='';
  if(m.trace.results){
   const index=snapshot.state.messages.indexOf(m),declaration=snapshot.state.messages.slice(0,Math.max(0,index)).reverse().find(event=>event.kind==='pack-talk'&&event.mode==='action'&&event.character===m.character);
   if(declaration)resultContext+=`<details><summary>Declaración resuelta</summary><p>${esc(declaration.text)}</p></details>`;
   const goals=snapshot.state.narrativeView?.objectives||[],proof=m.objectiveResolution,goal=goals.find(goal=>goal.id===proof?.objective);
   if(proof?.met)resultContext+=`<p>Objetivo completado: ${esc(goal?.title||'objetivo registrado')}.</p>`;
   else if(proof||goals.length)resultContext+='<p>Esta resolución no registra ningún objetivo completado.</p>';
  }
  return `<article><h4>${esc(m.speaker)} · ${esc(doc.actions[m.action]?.label||m.action)}</h4>${m.trace.results?`<section class="pack-confirmed-results"><h4>Resultado confirmado</h4>${Object.entries(m.trace.results).map(([id,value])=>`<p><strong>${esc(doc.fields[id]?.label||id)}: ${esc(shown(value))}</strong></p>`).join('')}${resultContext}</section>`:''}${Object.entries(m.trace.rolls).filter(([,r])=>r.rolled).map(([id,r])=>`<p>${esc(id)}: ${esc(r.values.join(', '))} → ${r.total} · ${r.origin==='physical'?'dados físicos':'servidor'}</p>`).join('')}${Object.entries(m.trace.changes).filter(([id])=>!Object.hasOwn(m.trace.results||{},id)).map(([id,v])=>`<p>${esc(doc.fields[id]?.label||id)}: ${esc(shown(v.before))} → ${esc(shown(v.after))}</p>`).join('')}${m.trace.triggers.map(t=>`<p>Consecuencia automática: ${esc(doc.triggers[t.id]?.label||t.id)}</p>`).join('')}</article>`;
 }
 function followStory(key){if(!$('#app').hidden&&scope()===key)($('#packStoryResolve')||$('#packStoryContinue')||$('#packStoryTalk'))?.scrollIntoView({block:'nearest'});}
 function renderAdventure(root,doc){
  if(snapshot.state.package?.policy!=='provided-rules')return;
  const key=scope(),state=snapshot.state,me=snapshot.me,memory=state.narrativeView,own=state.characters.filter(c=>c.owner===me.id&&c.creationProgress?.complete!==false);
  const history=root.querySelector('.pack-history');history.querySelector('h3').textContent=memory?'Aventura y resoluciones':'Registro de resoluciones';
  const controls=document.createElement('div');controls.id='packAdventure';history.append(controls);
  if(!memory){
   controls.innerHTML=me.host&&own.length?`<h3>Jugar esta aventura</h3><p>El director abre una situación a partir del objetivo de la campaña. Solo se resuelven las mecánicas disponibles en el paquete.</p><form id="packStoryStart"><label>Tu personaje<select name="character">${own.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></label><button class="primary">Iniciar aventura con IA</button></form>`:'<p>Crea tu personaje para entrar en la aventura. El anfitrión inicia la escena compartida.</p>';
   if($('#packStoryStart')){
    const form=$('#packStoryStart'),sourceKey=key+':adventure-source',saved=drafts.get(sourceKey)||{};
    if(!state.adventureSourceView){
     form.querySelector('button').insertAdjacentHTML('beforebegin',`<details><summary>Usar una aventura aportada, opcional</summary><p>Texto de una aventura breve, hasta 12.000 caracteres. La fuente no añade reglas al paquete.</p><label>Título de la aventura<input name="sourceTitle" maxlength="100" value="${esc(saved.title||'')}"></label><label>Texto privado de preparación<textarea name="sourceText" maxlength="12000" rows="5">${esc(saved.text||'')}</textarea></label><label>Leer un archivo de texto local<input id="packAdventureFile" type="file" accept=".txt,.md,text/plain,text/markdown"></label><label class="check"><input name="sourceUse" type="checkbox" ${saved.use?'checked':''}> Puedo utilizar esta aventura como preparación de esta partida</label></details>`);
     const remember=original=>{
      const previous=drafts.get(sourceKey)||{},displayed=form.elements.sourceText.value;
      const text=typeof original==='string'?original:previous.text?.replace(/\r\n?/g,'\n')===displayed?previous.text:displayed;
      drafts.set(sourceKey,{...previous,title:form.elements.sourceTitle.value,text,use:form.elements.sourceUse.checked});
     };
     form.oninput=remember;form.onchange=remember;
     $('#packAdventureFile').accept='.txt,.md,.json,text/plain,text/markdown,application/json';
     if(saved.plan)form.insertAdjacentHTML('afterbegin','<p class="notice" data-plan-note>Preparación estructurada cargada: incluye objetivos y descubrimientos. Si editas su fuente, vuelve a cargar el archivo antes de iniciar.</p>');
     $('#packAdventureFile').onchange=run(async e=>{
      const file=e.target.files[0];if(!file)return;
      const structured=/\.json$/i.test(file.name);
      if(file.size>(structured?60000:48000)||! /\.(txt|md|json)$/i.test(file.name))throw Error('Usa texto .txt/.md de hasta 48.000 bytes o una preparación .json de hasta 60.000 bytes.');
      const loaded=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());sameCampaign(key);
      const plan=structured?JSON.parse(loaded):null;
      if(plan&&(plan.format!=='cronicas-adventure-plan-1'||typeof plan.source?.text!=='string'||typeof plan.source?.title!=='string'))throw Error('Este JSON no es una preparación de aventura compatible.');
      if(structured&&!plan)throw Error('La preparación debe ser un objeto JSON.');
      const text=plan?plan.source.text:loaded;
      if(text.length>12000)throw Error('El texto supera los 12.000 caracteres.');
      drafts.set(sourceKey,{...(drafts.get(sourceKey)||{}),plan});
      if(plan)form.elements.sourceTitle.value=plan.source.title;
      form.elements.sourceText.value=text;if(!form.elements.sourceTitle.value)form.elements.sourceTitle.value=file.name.replace(/\.[^.]+$/,'').slice(0,100);remember(text);
      form.querySelector('[data-plan-note]')?.remove();
      if(plan)form.insertAdjacentHTML('afterbegin','<p class="notice" data-plan-note>Preparación estructurada cargada; el servidor comprobará su paquete, objetivos y citas antes de llamar al director.</p>');
     });
    }
    form.onsubmit=run(async e=>{
     sameCampaign(key);const fields=e.target.elements,data={character:fields.character.value};
     if(fields.sourceText?.value.trim()){
      if(!fields.sourceUse.checked||!fields.sourceTitle.value.trim())throw Error('Indica el título y confirma que puedes utilizar la aventura aportada.');
      const original=drafts.get(sourceKey)?.text;
      const plan=drafts.get(sourceKey)?.plan;
      if(plan){
       if(fields.sourceTitle.value!==plan.source.title||fields.sourceText.value!==plan.source.text.replace(/\r\n?/g,'\n'))throw Error('La fuente editada difiere de la preparación; vuelve a cargar el archivo o usa un archivo de texto sin preparación.');
       Object.assign(data,{plan,sourcePolicy:'provided-adventure'});
      }else Object.assign(data,{sourceTitle:fields.sourceTitle.value,sourceText:typeof original==='string'&&original.replace(/\r\n?/g,'\n')===fields.sourceText.value?original:fields.sourceText.value,sourcePolicy:'provided-adventure'});
     }
     await act('start_pack_adventure',data);drafts.delete(sourceKey);followStory(key);
    });
   }
   return;
  }
  $$('[data-pack-action]').forEach(b=>b.remove());
  const pending=memory.pending,continuation=memory.continuation;
  controls.innerHTML=`<details><summary>Recordar lo ocurrido</summary><p>${esc(memory.summary)}</p></details>${pending?`<section class="pack-request"><h3>${esc(doc.actions[pending.action].label)}</h3><p>${esc(state.characters.find(c=>c.id===pending.character)?.name)} · ${esc(pending.reason)}</p><div id="packRequestBody"></div></section>`:''}${continuation?'<p>La ficha y los dados ya están guardados. Falta narrar ese resultado.</p><button id="packStoryContinue" class="primary">Continuar relato con IA</button>':''}${own.length?`<form id="packStoryTalk"><h3>Tu intervención</h3><label>Personaje<select name="character">${own.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></label><label>Intervención<select name="mode"><option value="action">Declarar acción</option><option value="dialogue">Hablar en personaje</option><option value="ooc">Fuera de personaje · sin IA</option></select></label><label>¿Qué haces o dices?<textarea name="text" maxlength="4000" rows="3" required></textarea></label><button class="primary">Enviar intervención</button></form>`:'<p>Necesitas un personaje propio para intervenir.</p>'}`;
  const npcKey=key+':known-npcs',npcs=memory.npcs||[];
  if(state.adventureSourceView)controls.insertAdjacentHTML('afterbegin',`<p class="pack-source-note">Aventura aportada: ${esc(state.adventureSourceView.title)}</p>`);
  controls.querySelector('details').insertAdjacentHTML('afterend',`<details id="packKnownNpcs" ${drafts.get(npcKey)?'open':''}><summary>Personajes que conocéis${npcs.length?` · ${npcs.length}`:''}</summary>${npcs.length?npcs.map(npc=>`<article><h4>${esc(npc.name)}</h4><p>${esc(npc.public||'Sin más notas conocidas por el grupo.')}</p></article>`).join(''):'<p>Aún no hay personajes anotados.</p>'}</details>`);
  $('#packKnownNpcs').ontoggle=e=>{if(e.target.isConnected)drafts.set(npcKey,e.target.open);};
  const goalKey=key+':objectives',goals=memory.objectives||[];
  $('#packKnownNpcs').insertAdjacentHTML('afterend',`<details id="packObjectives" ${drafts.get(goalKey)?'open':''}><summary>Objetivos de la aventura${goals.length?` · ${goals.filter(g=>g.status==='completed').length}/${goals.length}`:''}</summary><p>Son oportunidades de la aventura; tú decides cómo actuar.</p>${goals.length?goals.map(goal=>`<article data-pack-objective="${esc(goal.id)}"><h4>${esc(goal.title)} · ${goal.status==='completed'?'Completado':'Abierto'}</h4><p>${esc(goal.detail)}</p>${goal.evidence?`<details><summary>Ver resultado que lo completó</summary><p>${esc(doc.actions[state.messages[goal.evidence.message]?.action]?.label||'Acción confirmada')} · ${esc(doc.fields[goal.evidence.field]?.label||goal.evidence.field)}: Sí. Revisión de ficha ${goal.evidence.sheetRevision}.</p></details>`:''}</article>`).join(''):'<p>Aún no hay objetivos anotados.</p>'}</details>`);
  $('#packObjectives').ontoggle=e=>{if(e.target.isConnected&&e.target.id==='packObjectives')drafts.set(goalKey,e.target.open);};
  if(memory.discoveries){
   const discoveryKey=key+':discoveries';
   $('#packObjectives').insertAdjacentHTML('afterend',`<details id="packDiscoveries" ${drafts.get(discoveryKey)?'open':''}><summary>Descubrimientos confirmados · ${memory.discoveries.length}</summary>${memory.discoveries.length?memory.discoveries.map(item=>`<article data-pack-discovery="${esc(item.id)}"><p>${esc(item.text)}</p><p>Consecuencia informativa de la preparación aportada, revelada por esta resolución.</p></article>`).join(''):'<p>Aún no se ha confirmado ningún descubrimiento de esta preparación.</p>'}</details>`);
   $('#packDiscoveries').ontoggle=e=>{if(e.target.isConnected)drafts.set(discoveryKey,e.target.open);};
  }
  const worldKey=key+':world-notes',places=memory.places||[],links=memory.relationships||[];
  $('#packObjectives').insertAdjacentHTML('afterend',`<details id="packWorld" ${drafts.get(worldKey)?'open':''}><summary>Lugares y vínculos</summary>${places.length?`<h4>Lugares recordados</h4>${places.map(place=>`<article data-pack-place="${esc(place.id)}"><h4>${esc(place.name)}</h4><p>${esc(place.public||'Sin más notas conocidas por el grupo.')}</p></article>`).join('')}`:''}${links.length?`<h4>Vínculos conocidos</h4><ul>${links.map(link=>`<li>${esc(link.fromName)} · ${esc(link.toName)}${link.public?`: ${esc(link.public)}`:''}</li>`).join('')}</ul>`:''}${!places.length&&!links.length?'<p>Aún no hay lugares ni vínculos anotados.</p>':''}</details>`);
  $('#packWorld').ontoggle=e=>{if(e.target.isConnected)drafts.set(worldKey,e.target.open);};
  if(pending){
   const actor=state.characters.find(c=>c.id===pending.character),action=doc.actions[pending.action],body=$('#packRequestBody');
   if(pending.objectiveCheck){
    const goal=goals.find(g=>g.id===pending.objectiveCheck.objective);
    body.insertAdjacentHTML('beforebegin',`<p class="notice">Objetivo vinculado: ${esc(goal?.title||pending.objectiveCheck.objective)}. Se completará si esta acción calcula ${esc(doc.fields[pending.objectiveCheck.field]?.label||pending.objectiveCheck.field)}: Sí con las opciones solicitadas. Si cambias esas opciones, el objetivo seguirá abierto.</p>`);
   }else if(goals.some(goal=>goal.status==='open')){
    body.insertAdjacentHTML('beforebegin','<p class="notice">Esta acción no está vinculada a un objetivo del diario. Resolverla no cerrará los objetivos abiertos.</p>');
   }
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
  const key=scope(),c=snapshot.state.characters.find(v=>v.id===characterId),doc=snapshot.state.package.document;
  const creating=c?.creationProgress?.complete===false&&c.creationProgress.next===actionId;
  const action=creating?{...doc.actions[actionId],inputs:c.creationInputs||doc.actions[actionId].inputs}:doc.actions[actionId];
  if(!c||!action)return;
  const draftKey=key+':'+c.id+':'+actionId,saved=drafts.get(draftKey)||{inputs:{},physical:{}};
  modal(`<div class="eyebrow">ACCIÓN · ${esc(c.name)}</div><h2>${esc(action.label)}</h2><p>El servidor comprueba requisitos y calcula las consecuencias definidas por el paquete.</p><form id="packAction">${Object.entries(action.inputs).map(([id,spec],i)=>`<label>${esc(spec.label)}${input(spec,i,saved.inputs[id]??spec.default)}</label>`).join('')}${action.rolls.length?`<details><summary>Usar dados físicos, opcional</summary><p>Deja cada campo vacío para tirar en el servidor. Si lo rellenas, escribe todos sus dados separados por comas.</p>${action.rolls.map((r,i)=>`<label>${esc(r.id)}<input name="dice${i}" value="${esc(saved.physical[r.id]||'')}" placeholder="Por ejemplo: 3, 4" inputmode="numeric"></label>`).join('')}</details>`:''}<button class="primary">Resolver ${esc(action.label)}</button></form>`);
  const form=$('#packAction');
  if(creating){$('#modalContent .eyebrow').textContent='CREAR PERSONAJE · '+c.name;$('#modalContent > p').textContent='Las opciones se comprueban con tus resultados anteriores.';form.querySelector('button.primary').textContent='Confirmar etapa';}
  if(creating)form.insertAdjacentHTML('beforebegin',`<p class="notice">Etapa ${c.creationProgress.completed+1} de ${c.creationProgress.total}. Los resultados anteriores ya están guardados; esta decisión no vuelve a tirarlos.</p><dl class="pack-fields">${Object.entries(doc.fields).map(([id,spec])=>`<div><dt>${esc(spec.label)}</dt><dd>${esc(shown(c.view.fields[id]))}</dd></div>`).join('')}</dl>`);
  function remember(){drafts.set(draftKey,{inputs:formValues(form,action),physical:Object.fromEntries(action.rolls.map((r,i)=>[r.id,form.elements['dice'+i].value]))});}
  form.oninput=remember;form.onchange=remember;
  form.onsubmit=run(async()=>{
   sameCampaign(key);remember();
   const physical=Object.fromEntries(action.rolls.flatMap((r,i)=>{
    const raw=form.elements['dice'+i].value.trim();if(!raw)return [];
    if(!/^\d+(\s*,\s*\d+)*$/.test(raw))throw Error('Escribe dados enteros separados por comas.');
    return [[r.id,raw.split(',').map(Number)]];
   }));
   await act(creating?'advance_pack_creation':'run_pack_action',{character:c.id,...(creating?{step:actionId}:{action:actionId}),inputs:formValues(form,action),...(Object.keys(physical).length?{physical}:{})});
   drafts.delete(draftKey);$('#modal').close();
   if(creating){const current=snapshot.state.characters.find(v=>v.id===c.id);if(current?.creationProgress?.complete===false)openAction(c.id,current.creationProgress.next);}
  });
 }
 function openCharacter(id){
  const c=snapshot.state.characters.find(v=>v.id===id);if(!c)return;
  const doc=snapshot.state.package.document;
  modal(`<div class="eyebrow">FICHA · ${esc(doc.name)}</div><h2>${esc(c.name)}</h2><dl class="pack-fields">${Object.entries(doc.fields).map(([key,spec])=>`<div><dt>${esc(spec.label)}</dt><dd>${esc(shown(c.view.fields[key]))}</dd></div>`).join('')}</dl><small>Valores calculados por el motor. Los cambios se realizan mediante acciones del paquete.</small>`);
  if(c.creation)$('#modalContent').insertAdjacentHTML('beforeend',`<details><summary>Origen de la ficha: elecciones y dados</summary>${(c.creation.steps||[c.creation]).map(entry=>`<h4>${esc(doc.actions[entry.trace.action].label)}</h4>${Object.entries(entry.inputs).map(([id,value])=>`<p>${esc(doc.actions[entry.trace.action].inputs[id]?.label||id)}: ${esc(shown(value))}</p>`).join('')}${Object.entries(entry.trace.rolls).filter(([,r])=>r.rolled).map(([id,r])=>`<p>${esc(id)}: ${esc(r.values.join(', '))} → ${r.total} · ${r.origin==='physical'?'dados físicos':'servidor'}</p>`).join('')}`).join('')}</details>`);
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
   const creation=creationSteps(doc).length?doc.actions[creationSteps(doc)[0]]:null,choiceKey=scope()+':creation-choices';
   if(creation){
    const saved=drafts.get(choiceKey)||{};
    $('#packCreate h3').textContent='Crear tu personaje';
    $('#packCreate p').textContent=creation.rolls.length?'Elige las opciones de tu personaje. Al confirmar, se tiran los dados y se calcula la ficha según este paquete.':'Elige las opciones de tu personaje. El motor comprobará los requisitos y calculará la ficha.';
    $('#packCreate button').insertAdjacentHTML('beforebegin',`<fieldset><legend>${esc(creation.label)}</legend>${Object.entries(creation.inputs).map(([id,spec],i)=>`<label>${esc(spec.label)}${input(spec,i,saved[id]??spec.default)}</label>`).join('')}</fieldset>`);
    $('#packCreate button').textContent=creation.rolls.length?'Crear personaje y tirar':'Crear personaje';
    if(creationSteps(doc).length>1){$('#packCreate p').textContent='Confirma la primera etapa. Después elegirás las siguientes opciones con sus resultados ya guardados.';$('#packCreate button').textContent=creation.rolls.length?'Comenzar creación y tirar':'Comenzar creación';}
   }
   $('#packCreate').oninput=e=>{drafts.set(nameKey,e.currentTarget.elements.name.value);if(creation)drafts.set(choiceKey,formValues(e.currentTarget,creation));};
   $('#packCreate').onchange=$('#packCreate').oninput;
   $('#packCreate').onsubmit=run(async e=>{await act('create_pack_sheet',{name:e.target.elements.name.value,...(creation?{inputs:formValues(e.target,creation)}:{})});drafts.delete(nameKey);drafts.delete(choiceKey);if($('#packCreate'))$('#packCreate').elements.name.value='';const pending=snapshot.state.characters.find(c=>c.owner===snapshot.me.id&&c.creationProgress?.complete===false);if(pending)openAction(pending.id,pending.creationProgress.next);});
  }
  $$('[data-pack-character]').forEach(b=>b.onclick=()=>openCharacter(b.dataset.packCharacter));
  $$('[data-pack-action]').forEach(b=>{const c=s.characters.find(c=>c.id===b.dataset.packTarget);if(reservedCreation(doc).has(b.dataset.packAction)||c?.creationProgress?.complete===false)b.remove();else b.onclick=()=>openAction(b.dataset.packTarget,b.dataset.packAction);});
  for(const c of s.characters.filter(c=>c.creationProgress?.complete===false)){
   const card=$$('[data-pack-character]').find(button=>button.dataset.packCharacter===c.id).closest('article');
   card.insertAdjacentHTML('beforeend',`<p class="notice">Creación en curso · ${c.creationProgress.completed} de ${c.creationProgress.total} etapas confirmadas.</p>${c.owner===me.id?`<button class="primary" data-pack-creation="${esc(c.id)}">Continuar creación</button>`:''}`);
  }
  $$('[data-pack-creation]').forEach(b=>b.onclick=()=>{const c=s.characters.find(c=>c.id===b.dataset.packCreation);openAction(c.id,c.creationProgress.next);});
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
