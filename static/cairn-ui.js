/* System workspace within the existing shell; all editing of loaded rolls is local. */
window.CairnUI=(()=>{
 let resourcesPromise;
 const labels={tools:'Herramientas',trinkets:'Objetos personales',armor:'Armadura',weapons:'Armas'};
 const option=(value,text,selected)=>`<option value="${esc(value)}" ${String(value)===String(selected)?'selected':''}>${esc(text)}</option>`;
 async function resources(){
  if(!resourcesPromise)resourcesPromise=api('/api/system-resources?system=cairn-1e').catch(e=>{resourcesPromise=null;throw e});
  return resourcesPromise;
 }
 function bonusTables(raw){return raw<=5?['tools','trinkets']:raw<=13?['expeditionary-gear']:raw<=17?['armor','weapons']:['spellbooks-d100']}
 function openCharacter(id){
  const c=snapshot.state.characters.find(c=>c.id===id);if(!c)return;
  modal(`<div class="eyebrow">PERSONAJE DE CAIRN 1e</div><h2>${esc(c.name)}</h2><p>${esc(c.background)} · ${c.age} años</p><div class="creator-stats">${Object.entries({...c.abilities,Protección:c.hitProtection+' / '+c.maxHitProtection,Armadura:c.armor,Espacios:c.inventorySlots+' / 10',Oro:c.gold}).map(([key,value])=>`<div><small>${esc(key)}</small><strong>${esc(value)}</strong></div>`).join('')}</div><h3>Equipo</h3>${c.inventory.map(e=>`<p>${esc(e.item)} · ${esc({carried:'transportado',equipped:'equipado',stored:'guardado fuera'}[e.state])}</p>`).join('')}<details><summary>Rasgos e identidad</summary>${Object.entries(c.traits).map(([key,value])=>`<p>${esc(key)}: ${esc(value)}</p>`).join('')}</details>${c.creation?`<details><summary>Origen de los cálculos</summary><p>Resultados originales conservados. Intercambio: ${esc(c.creation.swapped.join(' ↔ ')||'ninguno')}.</p>${Object.entries(c.creation.rolls).map(([key,values])=>`<p>${esc(key)}: ${values.join(', ')}</p>`).join('')}<small>La protección expresa capacidad de evitar daño; tener cero protección no equivale por sí solo a morir.</small></details>`:''}<p class="hint">Las acciones y la aventura automatizada de Cairn siguen en preparación.</p>`);
 }
 function renderCharacters(){
  $('#cairnCharacters').innerHTML=snapshot.state.characters.map(c=>`<article class="card"><h3>${esc(c.name)}</h3><p>${esc(c.background)} · Protección ${c.hitProtection} / ${c.maxHitProtection}</p><button data-cairn-character="${esc(c.id)}">Abrir ficha</button></article>`).join('');
  $$('[data-cairn-character]').forEach(button=>button.onclick=()=>openCharacter(button.dataset.cairnCharacter));
 }
 function renderArchive(){
  const archive=snapshot.state.importedDrafts||{};
  $('#cairnArchive').innerHTML=snapshot.me.host?`<div class="toolbar"><button id="cairnExport">Guardar copia de la campaña</button><label class="filebutton">Recuperar copia<input type="file" id="cairnImport" accept=".json,application/json"></label></div>${Object.keys(archive).length?`<div class="card"><h3>Borradores de la copia importada</h3><p>Recupera uno cada vez. Sus resultados originales se conservan; no se sustituye tu borrador actual.</p>${Object.keys(archive).map((key,i)=>`<button data-recover-draft="${esc(key)}" ${snapshot.state.creationDrafts?.[snapshot.me.id]?'disabled':''}>Recuperar borrador ${i+1}</button>`).join('')}</div>`:''}`:'';
  if($('#cairnExport'))$('#cairnExport').onclick=()=>$('#exportBtn').onclick();
  if($('#cairnImport'))$('#cairnImport').onchange=run(async e=>{
   const file=e.target.files[0];if(!file)return;
   if(file.size>8000000)throw Error('La copia supera el tamaño admitido.');
   if(!confirm('La copia sustituirá el estado de esta sala y sus personajes quedarán bajo tu control. Guarda antes una copia si quieres conservar el estado actual.'))return;
   await act('import',{campaign:JSON.parse(await file.text())});
  });
  $$('[data-recover-draft]').forEach(button=>button.onclick=run(()=>act('recover_imported_draft',{draft:button.dataset.recoverDraft})));
 }
 async function render(){
  const data=await resources();if(snapshot.state.ruleset!=='cairn-1e'||$('#app').hidden)return;
  $('#welcome').hidden=true;$('#savedLibraryPanel').hidden=true;$('#app').hidden=false;$('#app > .workspace').hidden=true;
  $('#campaignTitle').textContent=snapshot.title;$('#campaignMeta').textContent='Cairn 1e · creador en preparación';$('#inviteBtn').hidden=!snapshot.me.host;
  let root=$('#systemWorkspace');if(!root){root=document.createElement('section');root.id='systemWorkspace';root.className='system-workspace';$('#app').append(root)}
  root.hidden=false;
  const draft=snapshot.state.creationDrafts?.[snapshot.me.id],key=snapshot.id+':'+snapshot.me.id+':'+JSON.stringify(draft||{characters:snapshot.state.characters,imported:snapshot.state.importedDrafts});
  if(root.dataset.key===key){renderCharacters();renderArchive();return}root.dataset.key=key;
  root.innerHTML=`<div class="eyebrow">CAIRN · PRIMERA EDICIÓN</div><h2>Un personaje para adentrarse en el bosque</h2><p>Elige tu identidad y el equipo que llevarás. El motor conserva tus dados y calcula la ficha.</p><p class="notice">Cairn está en preparación: puedes guardar personajes, pero las acciones y la aventura automatizada aún no están disponibles.</p><div id="cairnCharacters"></div><div id="cairnArchive"></div><div id="cairnCreator"></div><small>Cairn, de Yochai Gal · <a href="${esc(data.tables.source)}" target="_blank" rel="noreferrer">SRD original</a> · <a href="${esc(data.tables.licenseUrl)}" target="_blank" rel="noreferrer">CC BY-SA 4.0</a>. Catálogo adaptado a datos y cálculos propios; términos originales en inglés.</small>`;
  renderCharacters();renderArchive();
  const target=$('#cairnCreator');
  if(!draft){
   target.innerHTML='<form id="cairnBegin" class="card"><h3>Preparar tus dados</h3><label>Tabla para inspirar el nombre<select name="nameTable"><option value="female-names">Nombres femeninos del SRD</option><option value="male-names">Nombres masculinos del SRD</option></select></label><p>Se tiran características, protección, edad, rasgos y equipo una sola vez. Después podrás revisar las opciones legales conservando los resultados.</p><button class="primary">Tirar y guardar el borrador</button></form>';
   if(snapshot.state.characters.some(c=>c.owner===snapshot.me.id))target.innerHTML='<details><summary>Crear otro personaje</summary>'+target.innerHTML+'</details>';
   $('#cairnBegin').onsubmit=run(e=>act('begin_character',values(e.target)));return;
  }
  const storageKey='cairn-creator:'+snapshot.id+':'+snapshot.me.id+':'+(draft.draftId||'legacy');let saved={};
  try{saved=JSON.parse(localStorage.getItem(storageKey)||'{}')}catch{}
  if(!saved||typeof saved!=='object'||Array.isArray(saved))saved={};
  target.innerHTML=`${!draft.bonus?`<form id="cairnBonus" class="card"><h3>Tu objeto adicional</h3><label>Elige dónde tirar<select name="table">${bonusTables(draft.bonusRoll).map(table=>option(table,labels[table]||table)).join('')}</select></label><small>La decisión se guarda antes de resolver la tirada. No se repite al recuperar el borrador.</small><button>Elegir tabla y tirar</button></form>`:''}<form id="cairnReview" class="card"><h3>Tu identidad y tus elecciones</h3><div class="row"><label>Nombre<select name="name">${data.tables.tables[draft.nameTable].map((name,i)=>option(i+1,name,saved.identity?.name||draft.identity.name)).join('')}</select></label><label>Apellido<select name="surname">${data.tables.tables.surnames.map((name,i)=>option(i+1,name,saved.identity?.surname||draft.identity.surname)).join('')}</select></label></div><label>Trasfondo<select name="background">${data.tables.tables.background.map((name,i)=>option(i+1,name,saved.identity?.background||draft.identity.background)).join('')}</select></label><label>Intercambiar dos resultados iniciales<select name="swap">${[['','Conservar el orden original'],['STR,DEX','Fuerza ↔ Destreza'],['STR,WIL','Fuerza ↔ Voluntad'],['DEX,WIL','Destreza ↔ Voluntad']].map(([value,text])=>option(value,text,saved.swap?.join(',')||'')).join('')}</select></label><div class="creator-stats" id="cairnStats"></div><div id="cairnWeaponChoices"></div><h4>Qué llevas contigo</h4><div id="cairnInventory"></div><p id="cairnPreviewStatus" role="status" aria-live="polite"></p><button class="primary" id="cairnConfirm" disabled>Guardar personaje</button><details><summary>Rasgos obtenidos</summary>${Object.entries(draft.identity.traits).map(([table,raw])=>`<p>${esc(table)}: ${esc(data.tables.tables[table][raw-1])}</p>`).join('')}<small>Son inspiración para interpretar; no deciden lo que piensa, siente o hace tu personaje.</small></details><small>Las elecciones se revisan localmente. Los dados originales ya están guardados en el servidor; las elecciones sin confirmar se recuerdan en este navegador. El transporte y ciertos usos de equipo siguen pendientes.</small></form>`;
  const form=$('#cairnReview');form.onsubmit=run(async()=>{await act('confirm_character',{choices:read()});localStorage.removeItem(storageKey)});
  $('#cairnWeaponChoices').innerHTML=CairnCreation.groups(draft,data.tables.tables).filter(g=>g.chooseOne).map(g=>`<label>${g.id==='bonus'?'Arma adicional':'Arma inicial'}<select data-weapon-group="${esc(g.id)}"><option value="">Elige una de las opciones obtenidas</option>${g.options.map(name=>option(name,name,saved.weapons?.[g.id])).join('')}</select></label>`).join('');
  function read(){
   return {identity:Object.fromEntries(['name','surname','background'].map(key=>[key,Number(form.elements[key].value)])),
    swap:form.elements.swap.value?form.elements.swap.value.split(','):[],
    weapons:Object.fromEntries([...form.querySelectorAll('[data-weapon-group]')].filter(e=>e.value).map(e=>[e.dataset.weaponGroup,e.value])),
    disposition:Object.fromEntries([...form.querySelectorAll('[data-item-state]')].map(e=>[e.dataset.itemState,e.value]))};
  }
  function paintInventory(choices){
   const entries=CairnCreation.equipment(draft,choices,data.tables.tables).inventory;
   $('#cairnInventory').innerHTML=entries.map(entry=>{const item=data.items[entry.item],selected=choices.disposition?.[entry.id]||'carried';return `<label>${esc(entry.item)} · ${item?item.slots+' espacios':'verificación pendiente'}<select data-item-state="${esc(entry.id)}">${[['carried','Llevar'],['stored','Guardar fuera'],...(item?.equip&&!item.requiresHandRuling?[['equipped','Llevar equipado']]:[])].map(([value,text])=>option(value,text,selected)).join('')}</select></label>`}).join('');
  }
  function update(rebuild=false){
   let choices=read();if(rebuild){paintInventory(choices);choices=read()}
   try{localStorage.setItem(storageKey,JSON.stringify(choices))}catch{toast('No se pudieron recordar las elecciones locales. Los dados del servidor se conservan.')}
   try{
    const value=CairnCreation.calculate(draft,choices,data);
    $('#cairnStats').innerHTML=Object.entries({...value.abilities,Protección:value.hitProtection,Armadura:value.armor,Espacios:value.inventorySlots,Edad:value.age,Oro:value.gold}).map(([key,total])=>`<div><small>${esc(key)}</small><strong>${total}</strong></div>`).join('');
    $('#cairnConfirm').disabled=value.pending.length>0;
    $('#cairnPreviewStatus').textContent=value.pending.join(' ')||'Cálculos revisados. Puedes guardar tu personaje.';
   }catch(error){$('#cairnConfirm').disabled=true;$('#cairnStats').innerHTML='';$('#cairnPreviewStatus').textContent=error.message}
  }
  paintInventory(saved);update();form.onchange=e=>update(!!e.target.dataset.weaponGroup);
  if($('#cairnBonus'))$('#cairnBonus').onsubmit=run(e=>act('choose_bonus',values(e.target)));
 }
 return {render,openCharacter};
})();
