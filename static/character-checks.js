/* Character checks use existing campaign actions; opening a sheet is local. */
const checkAbilities=[['str','Fuerza'],['dex','Destreza'],['con','Constitución'],['int','Inteligencia'],['wis','Sabiduría'],['cha','Carisma']];
const checkSaves=[['fort','Fortaleza'],['ref','Reflejos'],['will','Voluntad']];
function characterChecks(c){
 return [...checkAbilities.map(([key,name],i)=>({kind:'ability',key,name,total:Math.floor((c.abilities[i]-10)/2)})),...checkSaves.map(([key,name],i)=>({kind:'save',key,name,total:c.saves?.[i]})),...(c.skillTotals||[]).map(row=>({kind:'skill',key:row.name,name:row.name,total:row.total}))];
}
function sheetChecks(c){
 const allowed=(snapshot.me.host||c.owner===snapshot.me.id)&&characterIsConscious(c);
 const health=c.hp<=-c.abilities[2]?'Tu personaje ha muerto. Las tiradas de esta ficha están desactivadas.':c.hp<0&&!characterIsConscious(c)?'Tu personaje está inconsciente y no puede actuar.':c.hp<=0?'Consciente, pero incapacitado. Puedes moverte o usar una acción estándar, no ambas. Una acción fatigosa cuesta 1 PG y puede dejarte moribundo.':'';
 const checks=characterChecks(c),canRoll=allowed&&!c.conditions?.trim();
 const groups=[['skill','Habilidades'],['save','Salvaciones'],['ability','Características']];
 return `<section class="sheet-checks" data-roll-allowed="${canRoll?'1':'0'}">${health?`<p class="notice">${esc(health)}</p>`:''}${c.conditions?.trim()?'<p class="notice">Revisa las condiciones mediante resolución asistida antes de tirar automáticamente.</p>':''}<details class="sheet-free-roll"><summary>Hacer una tirada libre</summary><p class="hint">Elige qué quieres comprobar; el juego suma tu modificador guardado. Las tiradas solicitadas se resuelven directamente en la conversación. Guarda cualquier edición antes de tirar.</p><label>Qué quieres comprobar<select data-sheet-selection="${esc(c.id)}"><option value="" selected>Elige una opción</option>${groups.map(([kind,label])=>`<optgroup label="${label}">${checks.map((v,i)=>v.kind===kind?`<option value="${i}">${esc(v.name)} ${v.total>=0?'+':''}${Number(v.total)}</option>`:'').join('')}</optgroup>`).join('')}</select></label><button type="button" data-sheet-check="" data-check-character="${esc(c.id)}" data-check-key="" disabled>Tirar d20</button></details></section>`;
}
document.addEventListener('change',e=>{
 const select=e.target.closest('[data-sheet-selection]');if(!select)return;
 const sheet=select.closest('.sheet-checks'),button=sheet.querySelector('[data-sheet-check]');
 const character=snapshot.state.characters.find(c=>c.id===select.dataset.sheetSelection);
 if(!character){button.disabled=true;button.textContent='Vuelve a abrir la ficha';return;}
 sheet.dataset.rollAllowed=((snapshot.me.host||character.owner===snapshot.me.id)&&characterIsConscious(character)&&!character.conditions?.trim())?'1':'0';
 const check=select.value===''?null:characterChecks(character)[Number(select.value)];
 button.disabled=!check||sheet.dataset.rollAllowed!=='1';
 button.dataset.sheetCheck=check?.kind||'';button.dataset.checkKey=check?.key||'';
 button.textContent=check?`Tirar ${check.name} (${check.total>=0?'+':''}${check.total})`:'Tirar d20';
});
function skillFields(c){
 return `<label>Habilidades preparadas para tirar · una por línea: nombre | total<textarea name="skillTotalsInput" placeholder="Percepción | 6">${esc((c.skillTotals||[]).map(row=>row.name+' | '+row.total).join('\n'))}</textarea></label><p class="hint">Prepara solo habilidades cuyo uso sea legal y sus totales estén verificados: característica, rangos, bonificador de clase y demás modificadores ya incluidos. Las notas antiguas de habilidades se conservan.</p>`;
}
function parseSkillTotals(text){
 return String(text||'').split('\n').filter(line=>line.trim()).map(line=>{const match=line.match(/^([^|]+)\|\s*([+-]?\d+)\s*$/);if(!match)throw Error('Usa una habilidad por línea: nombre | total');return {name:match[1].trim(),total:Number(match[2])}});
}
function renderChecks(){
 const rows=snapshot.state.pending.filter(p=>p.check),me=snapshot.me;
 $('#requestCheck').hidden=!me.host||!snapshot.state.characters.some(c=>!c.enemy&&characterIsConscious(c)&&!c.conditions?.trim());
 $('#checkRequests').innerHTML=rows.map(p=>{
  const c=snapshot.state.characters.find(c=>c.id===p.check.character),allowed=c&&(me.host||c.owner===me.id);
  const name=c&&characterChecks(c).find(v=>v.kind===p.check.kind&&v.key===p.check.key)?.name||p.check.key;
  return `<article class="check-request"><strong>${esc(c?.name||'Personaje')} · ${esc(name)} · CD ${p.check.dc}</strong><p>${esc(p.reason)}</p><small>${esc(p.source)}</small><div class="toolbar"><button class="primary" data-resolve-check="${esc(p.check.id)}" ${!allowed?'disabled':''}>Tirar d20 y resolver</button>${p.investigation?`<button data-resolve-check="${esc(p.check.id)}" data-check-method="take10" ${!allowed?'disabled':''}>Elegir 10</button><button data-resolve-check="${esc(p.check.id)}" data-check-method="take20" ${!allowed?'disabled':''}>Elegir 20 · veinte búsquedas</button>`:''}${me.host?`<button data-cancel-check="${esc(p.check.id)}">Cancelar</button>`:''}</div></article>`;
 }).join('');
}
function requestCheckForm(){
 if(!snapshot.me.host)return;
 if(!snapshot.state.characters.length){toast('Crea primero un personaje');return}
 modal(`<h2>Solicitar una prueba</h2><form id="requestCheckForm"><label>Personaje<select name="character">${snapshot.state.characters.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></label><label>Prueba<select name="selection"></select></label><label>CD de la tarea o efecto<input name="dc" type="number" min="0" max="1000" value="15" required></label><label>Motivo<input name="reason" maxlength="500" required></label><p class="hint">Se pide al jugador que tire; el servidor aplica su modificador y determina el éxito. Daño, acciones y consecuencias especiales siguen su procedimiento correspondiente.</p><button class="primary">Solicitar tirada</button></form>`);
 const form=$('#requestCheckForm');
 function update(){const c=snapshot.state.characters.find(c=>c.id===form.elements.character.value);form.elements.selection.innerHTML=characterChecks(c).map((v,i)=>`<option value="${i}">${esc(v.name)} (${v.total>=0?'+':''}${v.total})</option>`).join('')}
 form.elements.character.onchange=update;update();
 form.onsubmit=run(async()=>{const c=snapshot.state.characters.find(c=>c.id===form.elements.character.value),check=characterChecks(c)[Number(form.elements.selection.value)];await act('request_check',{character:c.id,checkKind:check.kind,key:check.key,dc:Number(form.elements.dc.value),reason:form.elements.reason.value});$('#modal').close()});
}
document.addEventListener('click',e=>{
 const button=e.target.closest('[data-sheet-check],[data-resolve-check],[data-cancel-check]');if(!button)return;
 run(async()=>{
 if(button.dataset.sheetCheck){await act('check',{character:button.dataset.checkCharacter,checkKind:button.dataset.sheetCheck,key:button.dataset.checkKey});toast(snapshot.state.messages.at(-1).text)}
 else if(button.dataset.resolveCheck)await act('check',{request:button.dataset.resolveCheck,...(button.dataset.checkMethod?{method:button.dataset.checkMethod}:{})});
 else await act('cancel_check',{request:button.dataset.cancelCheck});
 })(e);
});
