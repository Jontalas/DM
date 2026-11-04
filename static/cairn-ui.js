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
 async function render(){
  const data=await resources();if(snapshot.state.ruleset!=='cairn-1e'||$('#app').hidden)return;
  $('#welcome').hidden=true;$('#savedLibraryPanel').hidden=true;$('#app').hidden=false;$('#app > .workspace').hidden=true;
  $('#campaignTitle').textContent=snapshot.title;$('#campaignMeta').textContent='Cairn 1e · creador en preparación';$('#inviteBtn').hidden=!snapshot.me.host;
  let root=$('#systemWorkspace');if(!root){root=document.createElement('section');root.id='systemWorkspace';root.className='system-workspace';$('#app').append(root)}
  root.hidden=false;
  const draft=snapshot.state.creationDrafts?.[snapshot.me.id],key=snapshot.id+':'+snapshot.me.id+':'+JSON.stringify(draft||null);
  if(root.dataset.key===key)return;root.dataset.key=key;
  root.innerHTML=`<div class="eyebrow">CAIRN · PRIMERA EDICIÓN</div><h2>Un personaje para adentrarse en el bosque</h2><p>Elige tu identidad y el equipo que llevarás. El motor conserva tus dados y calcula la ficha.</p><p class="notice">Cairn está en preparación: todavía no se puede confirmar el personaje ni iniciar una partida.</p><div id="cairnCreator"></div><small>Cairn, de Yochai Gal · <a href="${esc(data.tables.source)}" target="_blank" rel="noreferrer">SRD original</a> · <a href="${esc(data.tables.licenseUrl)}" target="_blank" rel="noreferrer">CC BY-SA 4.0</a>. Catálogo adaptado a datos y cálculos propios; términos originales en inglés.</small>`;
  const target=$('#cairnCreator');
  if(!draft){
   target.innerHTML='<form id="cairnBegin" class="card"><h3>Preparar tus dados</h3><label>Tabla para inspirar el nombre<select name="nameTable"><option value="female-names">Nombres femeninos del SRD</option><option value="male-names">Nombres masculinos del SRD</option></select></label><p>Se tiran características, protección, edad, rasgos y equipo una sola vez. Después podrás revisar las opciones legales conservando los resultados.</p><button class="primary">Tirar y guardar el borrador</button></form>';
   $('#cairnBegin').onsubmit=run(e=>act('begin_character',values(e.target)));return;
  }
  const storageKey='cairn-creator:'+snapshot.id+':'+snapshot.me.id;let saved={};
  try{saved=JSON.parse(localStorage.getItem(storageKey)||'{}')}catch{}
  if(!saved||typeof saved!=='object'||Array.isArray(saved))saved={};
  target.innerHTML=`${!draft.bonus?`<form id="cairnBonus" class="card"><h3>Tu objeto adicional</h3><label>Elige dónde tirar<select name="table">${bonusTables(draft.bonusRoll).map(table=>option(table,labels[table]||table)).join('')}</select></label><small>La decisión se guarda antes de resolver la tirada. No se repite al recuperar el borrador.</small><button>Elegir tabla y tirar</button></form>`:''}<form id="cairnReview" class="card"><h3>Tu identidad y tus elecciones</h3><div class="row"><label>Nombre<select name="name">${data.tables.tables[draft.nameTable].map((name,i)=>option(i+1,name,saved.identity?.name||draft.identity.name)).join('')}</select></label><label>Apellido<select name="surname">${data.tables.tables.surnames.map((name,i)=>option(i+1,name,saved.identity?.surname||draft.identity.surname)).join('')}</select></label></div><label>Trasfondo<select name="background">${data.tables.tables.background.map((name,i)=>option(i+1,name,saved.identity?.background||draft.identity.background)).join('')}</select></label><label>Intercambiar dos resultados iniciales<select name="swap">${[['','Conservar el orden original'],['STR,DEX','Fuerza ↔ Destreza'],['STR,WIL','Fuerza ↔ Voluntad'],['DEX,WIL','Destreza ↔ Voluntad']].map(([value,text])=>option(value,text,saved.swap?.join(',')||'')).join('')}</select></label><div class="creator-stats" id="cairnStats"></div><div id="cairnWeaponChoices"></div><h4>Qué llevas contigo</h4><div id="cairnInventory"></div><p id="cairnPreviewStatus" role="status" aria-live="polite"></p><details><summary>Rasgos obtenidos</summary>${Object.entries(draft.identity.traits).map(([table,raw])=>`<p>${esc(table)}: ${esc(data.tables.tables[table][raw-1])}</p>`).join('')}<small>Son inspiración para interpretar; no deciden lo que piensa, siente o hace tu personaje.</small></details><small>Las elecciones se revisan localmente. Los dados originales ya están guardados en el servidor; las elecciones sin confirmar se recuerdan en este navegador. El transporte y ciertos usos de equipo siguen pendientes.</small></form>`;
  const form=$('#cairnReview');form.onsubmit=e=>e.preventDefault();
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
    $('#cairnPreviewStatus').textContent=value.pending.join(' ')||'Cálculos revisados. La confirmación del personaje sigue en preparación.';
   }catch(error){$('#cairnStats').innerHTML='';$('#cairnPreviewStatus').textContent=error.message}
  }
  paintInventory(saved);update();form.onchange=e=>update(!!e.target.dataset.weaponGroup);
  if($('#cairnBonus'))$('#cairnBonus').onsubmit=run(e=>act('choose_bonus',values(e.target)));
 }
 return {render};
})();
