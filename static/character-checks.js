/* Character checks use existing campaign actions; opening a sheet is local. */
const checkAbilities=[['str','Fuerza'],['dex','Destreza'],['con','Constitución'],['int','Inteligencia'],['wis','Sabiduría'],['cha','Carisma']];
const checkSaves=[['fort','Fortaleza'],['ref','Reflejos'],['will','Voluntad']];
const characterViews=new WeakMap();
function bindCharacterViews(){for(const view of $$('#modal .sheet-checks,#modal #characterForm,#modal #requestCheckForm'))characterViews.set(view,readViewScope(view))}
function characterViewIsCurrent(view){return !!view&&$('#modal').open&&$('#modal').contains(view)&&readViewIsCurrent(characterViews.get(view),view)}
function checkCharacterView(view){
 if(characterViewIsCurrent(view))return true;
 if(!view?.isConnected||!$('#modal').open||!$('#modal').contains(view))return false;
 const message=view.id==='requestCheckForm'?'La partida ha cambiado. Cierra esta solicitud y vuelve a abrirla en la partida correcta.':'La partida ha cambiado. Cierra esta ficha y vuelve a abrir la que quieras consultar.';
 let status=$('#modal .sheet-context-status');if(!status){status=document.createElement('p');status.className='notice sheet-context-status';status.setAttribute('role','status');status.tabIndex=-1;$('#modalContent').prepend(status)}
 status.textContent=message;view.querySelectorAll('[data-sheet-check],button.primary').forEach(button=>button.disabled=true);status.focus();toast(message);return false;
}
function renderDiceEntry(){
 const characters=snapshot.state.characters.filter(c=>c.owner===snapshot.me.id&&!c.enemy);
 $('#diceCharacters').innerHTML='<h3>Tira desde tu ficha</h3>'+(characters.length?'<p>Elige qué quieres comprobar. El juego suma el modificador guardado en tu ficha; las tiradas solicitadas se resuelven en la conversación.</p>'+characters.map(c=>`<button type="button" data-dice-character="${esc(c.id)}">Abrir tiradas de ${esc(c.name)}</button>`).join(' '):'<p>Crea tu personaje para tirar con los valores de su ficha. Las herramientas manuales están disponibles más abajo.</p><button type="button" data-dice-create>Crear mi personaje</button>');
}
document.addEventListener('click',e=>{
 const button=e.target.closest('[data-dice-character],[data-dice-create],[data-dice-view]');if(!button)return;
 run(()=>{
  if(button.hasAttribute('data-dice-create')){characterForm();return}
  if(button.dataset.diceView&&!checkCharacterView($('#modal .sheet-checks')))return;
  const character=snapshot.state.characters.find(c=>c.id===(button.dataset.diceCharacter||button.dataset.diceView)&&c.owner===snapshot.me.id&&!c.enemy);
  if(!character)throw Error('Esta ficha ya no está disponible. Vuelve a elegir tu personaje.');
  if(button.dataset.diceView){characterForm(character.id);return}
  modal(`<div class="eyebrow">TIRADA DE TU PERSONAJE</div><h2>¿Qué quieres comprobar?</h2><p><strong>${esc(character.name)}</strong></p>${!character.creation||character.creation.manualOverride?'<p class="hint">Esta ficha contiene valores preparados manualmente. Puedes consultar su origen en la ficha completa.</p>':''}${sheetChecks(character,false)}<button type="button" data-dice-view="${esc(character.id)}">Ver ficha completa</button>`);
  const details=$('#modal .sheet-free-roll');if(details){details.dataset.fromDice='1';details.open=true;details.querySelector('[data-sheet-selection]')?.focus()}
 })(e);
});
function characterChecks(c){
 return [...checkAbilities.map(([key,name],i)=>({kind:'ability',key,name,total:Math.floor((c.abilities[i]-10)/2)})),...checkSaves.map(([key,name],i)=>({kind:'save',key,name,total:c.saves?.[i]})),...(c.skillTotals||[]).map(row=>({kind:'skill',key:row.name,name:row.name,total:row.total}))];
}
function selectedCharacterCheck(select,c){const option=select.selectedOptions[0];return c&&option?characterChecks(c).find(check=>check.kind===option.dataset.optionKind&&check.key===option.dataset.optionKey):null}
function sheetChecks(c,showEditReminder=true){
 const mayControl=snapshot.me.host||c.owner===snapshot.me.id,allowed=mayControl&&characterIsConscious(c);
 const subject=c.npcCreation?'Este PNJ':c.owner===snapshot.me.id&&!c.enemy?'Tu personaje':'Este personaje';
 const health=c.hp<=-c.abilities[2]?subject+' ha muerto. Las tiradas de esta ficha están desactivadas.':c.hp<0&&!characterIsConscious(c)?subject+' está inconsciente y no puede actuar.':c.hp<=0?subject+' está consciente, pero incapacitado. Puede moverse o usar una acción estándar, no ambas. Una acción fatigosa cuesta 1 PG y puede dejarlo moribundo.':'';
 const checks=characterChecks(c),canRoll=allowed&&!c.conditions?.trim();
 const groups=[['skill','Habilidades'],['save','Salvaciones'],['ability','Características']];
 return `<section class="sheet-checks" data-roll-allowed="${canRoll?'1':'0'}">${health?`<p class="notice">${esc(health)}</p>`:''}${c.conditions?.trim()?'<p class="notice">Revisa las condiciones mediante resolución asistida antes de tirar automáticamente.</p>':''}<details class="sheet-free-roll"><summary>Hacer una tirada libre</summary><p class="hint">${mayControl?'Elige qué quieres comprobar; el juego suma tu modificador guardado. Las tiradas solicitadas se resuelven directamente en la conversación.'+(showEditReminder?' Guarda cualquier edición antes de tirar.':''):'No controlas esta ficha. Puedes consultar sus modificadores; las tiradas corresponden a su propietario o al anfitrión.'}</p><label>Qué quieres comprobar<select data-sheet-selection="${esc(c.id)}"><option value="" selected>Elige una opción</option>${groups.map(([kind,label])=>`<optgroup label="${label}">${checks.map((v,i)=>v.kind===kind?`<option value="${i}" data-option-kind="${esc(v.kind)}" data-option-key="${esc(v.key)}">${esc(v.name)} ${v.total>=0?'+':''}${Number(v.total)}</option>`:'').join('')}</optgroup>`).join('')}</select></label><button type="button" data-sheet-check="" data-check-character="${esc(c.id)}" data-check-key="" disabled>Tirar d20</button></details></section>`;
}
document.addEventListener('change',e=>{
 const select=e.target.closest('[data-sheet-selection]');if(!select)return;
 const sheet=select.closest('.sheet-checks'),button=sheet.querySelector('[data-sheet-check]');
 if(!checkCharacterView(sheet))return;
 const character=snapshot.state.characters.find(c=>c.id===select.dataset.sheetSelection);
 if(!character){button.disabled=true;button.textContent='Vuelve a abrir la ficha';return;}
 sheet.dataset.rollAllowed=((snapshot.me.host||character.owner===snapshot.me.id)&&characterIsConscious(character)&&!character.conditions?.trim())?'1':'0';
 const check=selectedCharacterCheck(select,character);
 button.disabled=!check||sheet.dataset.rollAllowed!=='1';
 button.dataset.sheetCheck=check?.kind||'';button.dataset.checkKey=check?.key||'';
 button.textContent=check?`Tirar ${check.name} (${check.total>=0?'+':''}${check.total})`:select.value?'Vuelve a abrir la ficha':'Tirar d20';
});
function skillFields(c){
 return `<label>Habilidades preparadas para tirar · una por línea: nombre | total<textarea name="skillTotalsInput" placeholder="Percepción | 6">${esc((c.skillTotals||[]).map(row=>row.name+' | '+row.total).join('\n'))}</textarea></label><p class="hint">Prepara solo habilidades cuyo uso sea legal y sus totales estén verificados: característica, rangos, bonificador de clase y demás modificadores ya incluidos. Las notas antiguas de habilidades se conservan.</p>`;
}
function parseSkillTotals(text){
 return String(text||'').split('\n').filter(line=>line.trim()).map(line=>{const match=line.match(/^([^|]+)\|\s*([+-]?\d+)\s*$/);if(!match)throw Error('Usa una habilidad por línea: nombre | total');return {name:match[1].trim(),total:Number(match[2])}});
}
function pendingCheckUnavailable(p,c){
 if(!c)return 'El personaje ya no está disponible en esta mesa.';
 if(p.investigation&&c.owner!==snapshot.me.id)return 'Esta búsqueda la resuelve su propietario. Espera su tirada.';
 if(!characterIsConscious(c))return 'El personaje no puede tirar mientras esté inconsciente o muerto.';
 if(c.conditions?.trim())return 'Hay condiciones que requieren revisar esta prueba antes de resolverla.';
 if(p.investigation&&snapshot.state.board.active)return 'La investigación automática no está disponible durante el combate.';
 if(p.investigation&&!canExplorePrepared(c))return 'Esta investigación todavía no cubre el estado actual de tu personaje.';
 if(p.investigation&&snapshot.state.pfContinuation){
  const npc=snapshot.state.characters.find(v=>v.id===snapshot.state.pfEncounter.npc);
  if(npc&&((npc.hp<0&&npc.hp>-npc.abilities[2]&&!(snapshot.state.pfNpcRecoveryView?.canContinue||snapshot.state.pfLightExplorationView?.canExplore))||npc.conditions?.trim()))return 'La guardiana necesita resolver su estado antes de continuar investigando.';
 }
 return '';
}
function renderChecks(){
 const rows=snapshot.state.pending.filter(p=>p.check),me=snapshot.me;
 $('#requestCheck').hidden=!me.host||!snapshot.state.characters.some(c=>!c.enemy&&characterIsConscious(c)&&!c.conditions?.trim());
 $('#checkRequests').innerHTML=rows.map(p=>{
  const c=snapshot.state.characters.find(c=>c.id===p.check.character),blocked=pendingCheckUnavailable(p,c),allowed=c&&(me.host||c.owner===me.id)&&!blocked;
  const name=c&&characterChecks(c).find(v=>v.kind===p.check.kind&&v.key===p.check.key)?.name||p.check.key;
  return `<article class="check-request"><strong>${esc(c?.name||'Personaje')} · ${esc(name)} · CD ${p.check.dc}</strong><p>${esc(p.reason)}</p><small>${esc(p.source)}</small>${blocked?`<p class="notice">${esc(blocked)}</p>`:''}<div class="toolbar"><button class="primary" data-resolve-check="${esc(p.check.id)}" ${!allowed?'disabled':''}>Tirar d20 y resolver</button>${p.investigation?`<button data-resolve-check="${esc(p.check.id)}" data-check-method="take10" ${!allowed?'disabled':''}>Elegir 10</button><button data-resolve-check="${esc(p.check.id)}" data-check-method="take20" ${!allowed?'disabled':''}>Elegir 20 · veinte búsquedas</button>`:''}${me.host?`<button data-cancel-check="${esc(p.check.id)}">Cancelar</button>`:''}</div></article>`;
 }).join('');
}
function requestCheckForm(){
 if(!snapshot.me.host)return;
 if(!snapshot.state.characters.length){toast('Crea primero un personaje');return}
 modal(`<h2>Solicitar una prueba</h2><form id="requestCheckForm"><label>Personaje<select name="character">${snapshot.state.characters.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></label><label>Prueba<select name="selection"></select></label><label>CD de la tarea o efecto<input name="dc" type="number" min="0" max="1000" value="15" required></label><label>Motivo<input name="reason" maxlength="500" required></label><p class="hint">Se pide al jugador que tire; el servidor aplica su modificador y determina el éxito. Daño, acciones y consecuencias especiales siguen su procedimiento correspondiente.</p><button class="primary">Solicitar tirada</button></form>`);
 const form=$('#requestCheckForm');
 function update(){if(!checkCharacterView(form))return;const c=snapshot.state.characters.find(c=>c.id===form.elements.character.value);if(!c){form.elements.selection.innerHTML='';form.querySelector('button.primary').disabled=true;toast('Esta ficha ya no está disponible. Cierra la solicitud y vuelve a elegir.');return}form.elements.selection.innerHTML=characterChecks(c).map((v,i)=>`<option value="${i}" data-option-kind="${esc(v.kind)}" data-option-key="${esc(v.key)}">${esc(v.name)} (${v.total>=0?'+':''}${v.total})</option>`).join('')}
 form.elements.character.onchange=update;update();
 form.onsubmit=run(async()=>{if(!checkCharacterView(form))return;const c=snapshot.state.characters.find(c=>c.id===form.elements.character.value),check=selectedCharacterCheck(form.elements.selection,c);if(!check){toast('La prueba ya no est\u00e1 disponible. Cierra la solicitud y vuelve a elegir.');return}await act('request_check',{character:c.id,checkKind:check.kind,key:check.key,dc:Number(form.elements.dc.value),reason:form.elements.reason.value});if(characterViewIsCurrent(form)){$('#modal').close();chooseTab('story')}});
}
document.addEventListener('click',e=>{
 const button=e.target.closest('[data-sheet-check],[data-resolve-check],[data-cancel-check]');if(!button)return;
 run(async()=>{
 if(button.dataset.sheetCheck){const sheet=button.closest('.sheet-checks');if(!checkCharacterView(sheet))return;await act('check',{character:button.dataset.checkCharacter,checkKind:button.dataset.sheetCheck,key:button.dataset.checkKey});if(characterViewIsCurrent(sheet)){if(button.closest('.sheet-free-roll')?.dataset.fromDice==='1'){$('#modal').close();chooseTab('story')}toast(snapshot.state.messages.at(-1).text)}}
 else if(button.dataset.resolveCheck)await act('check',{request:button.dataset.resolveCheck,...(button.dataset.checkMethod?{method:button.dataset.checkMethod}:{})});
 else await act('cancel_check',{request:button.dataset.cancelCheck});
 })(e);
});
