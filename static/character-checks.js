/* Character checks use existing campaign actions; opening a sheet is local. */
const checkAbilities=[['str','Fuerza'],['dex','Destreza'],['con','Constitución'],['int','Inteligencia'],['wis','Sabiduría'],['cha','Carisma']];
const checkSaves=[['fort','Fortaleza'],['ref','Reflejos'],['will','Voluntad']];
function characterChecks(c){
 return [...checkAbilities.map(([key,name],i)=>({kind:'ability',key,name,total:Math.floor((c.abilities[i]-10)/2)})),...checkSaves.map(([key,name],i)=>({kind:'save',key,name,total:c.saves?.[i]})),...(c.skillTotals||[]).map(row=>({kind:'skill',key:row.name,name:row.name,total:row.total}))];
}
function sheetChecks(c){
 const allowed=(snapshot.me.host||c.owner===snapshot.me.id)&&c.hp>=0;
 return `<section class="sheet-checks"><h3>Tirar desde la ficha</h3><p class="hint">Usa los valores guardados. Guarda primero cualquier edición. Una tirada libre muestra el total; las solicitadas por el maestro comparan también con su CD.</p><div class="toolbar">${characterChecks(c).map(v=>`<button type="button" data-sheet-check="${esc(v.kind)}" data-check-character="${esc(c.id)}" data-check-key="${esc(v.key)}" ${!allowed||c.conditions?.trim()?'disabled':''}>${esc(v.name)} ${Number(v.total)>=0?'+':''}${Number(v.total)}</button>`).join('')}</div>${c.conditions?.trim()?'<p class="notice">Revisa las condiciones mediante resolución asistida antes de tirar automáticamente.</p>':''}</section>`;
}
function skillFields(c){
 return `<label>Habilidades preparadas para tirar · una por línea: nombre | total<textarea name="skillTotalsInput" placeholder="Percepción | 6">${esc((c.skillTotals||[]).map(row=>row.name+' | '+row.total).join('\n'))}</textarea></label><p class="hint">Prepara solo habilidades cuyo uso sea legal y sus totales estén verificados: característica, rangos, bonificador de clase y demás modificadores ya incluidos. Las notas antiguas de habilidades se conservan.</p>`;
}
function parseSkillTotals(text){
 return String(text||'').split('\n').filter(line=>line.trim()).map(line=>{const match=line.match(/^([^|]+)\|\s*([+-]?\d+)\s*$/);if(!match)throw Error('Usa una habilidad por línea: nombre | total');return {name:match[1].trim(),total:Number(match[2])}});
}
function renderChecks(){
 const rows=snapshot.state.pending.filter(p=>p.check),me=snapshot.me;
 $('#requestCheck').hidden=!me.host;
 $('#checkRequests').innerHTML=rows.map(p=>{
  const c=snapshot.state.characters.find(c=>c.id===p.check.character),allowed=c&&(me.host||c.owner===me.id);
  const name=c&&characterChecks(c).find(v=>v.kind===p.check.kind&&v.key===p.check.key)?.name||p.check.key;
  return `<article class="check-request"><strong>${esc(c?.name||'Personaje')} · ${esc(name)} · CD ${p.check.dc}</strong><p>${esc(p.reason)}</p><small>${esc(p.source)}</small><div class="toolbar"><button class="primary" data-resolve-check="${esc(p.check.id)}" ${!allowed?'disabled':''}>Tirar d20 y resolver</button>${me.host?`<button data-cancel-check="${esc(p.check.id)}">Cancelar</button>`:''}</div></article>`;
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
 else if(button.dataset.resolveCheck)await act('check',{request:button.dataset.resolveCheck});
 else await act('cancel_check',{request:button.dataset.cancelCheck});
 })(e);
});
