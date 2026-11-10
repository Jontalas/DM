let libraryWarningShown=false;
function rememberCampaign(){
 try{CampaignLibrary.record(localStorage,snapshot,token);renderSavedCampaigns()}
 catch(error){if(!libraryWarningShown){toast('No se pudo actualizar la lista local de accesos. La campaña sigue guardada en el servidor. '+error.message);libraryWarningShown=true}}
}
function ensureCampaignCanChange(destination){
 const pending=JSON.parse(localStorage.getItem('cronicas-pending')||'null');
 if(busy)throw Error('Espera a que termine la operación actual antes de cambiar de partida.');
 if(pending&&!(pending.token!==token&&pending.token===destination))throw Error('Recupera o termina el envío pendiente antes de cambiar de campaña.');
}
async function openPendingCampaign(){
 const pending=JSON.parse(localStorage.getItem('cronicas-pending')||'null');
 const entry=CampaignLibrary.read(localStorage).entries.find(v=>v.token===pending?.token);
 if(!entry)throw Error('Abre la pestaña de la partida que tiene el envío pendiente para recuperarlo.');
 await openSavedCampaign(entry.id);
}
async function openSavedCampaign(id,characterId){
 const entry=CampaignLibrary.read(localStorage).entries.find(v=>v.id===id);
 if(!entry)throw Error('Acceso de campaña no encontrado');
 ensureCampaignCanChange(entry.token);
 busy=true;renderComposerAvailability();
 const originalDialog=$('#modalContent').firstElementChild,hadDialog=$('#modal').open;
 try{
  const next=await api('/api/state',undefined,entry.token);
  if(next.id!==entry.campaign||next.me.id!==entry.player)throw Error('La credencial no coincide con el acceso guardado');
  token=entry.token;localStorage.setItem('cronicas-token',token);
  bookReader.reset();document.body.classList.remove('reader-wide');readerExpanded=false;
  snapshot=next;snapshotToken=token;lastVersion=next.version;path=[];ruler=[];rememberCampaign();renderSyncStatus();render();
  const sameDialog=$('#modal').open===hadDialog&&$('#modalContent').firstElementChild===originalDialog;
  if(sameDialog&&hadDialog)$('#modal').close();
  if(sameDialog&&characterId&&next.state.characters.some(c=>c.id===characterId&&c.owner===next.me.id)){
   if(next.state.ruleset==='rule-pack')RulePackUI.openCharacter(characterId);else if(next.state.ruleset==='cairn-1e')CairnUI.openCharacter(characterId);else characterForm(characterId);
  }
 }finally{busy=false;renderComposerAvailability()}

}
function libraryHtml(library,inCampaign=false){
 if(!library.entries.length)return '<p>Tus partidas y personajes aparecerán aquí al entrar en una campaña.</p>';
 return library.entries.map(entry=>{
  const characters=entry.characters.map(c=>`<div class="library-character"><strong>${esc(c.name)}</strong><small>${entry.ruleset==='cairn-1e'?'Cairn 1e · '+esc(c.background):esc(c.race)+' · '+esc(c.class)+' '+esc(c.level)}</small><div class="toolbar"><button data-library-open="${esc(entry.id)}" data-library-character="${esc(c.id)}">Abrir personaje original</button>${inCampaign&&entry.ruleset==='pathfinder-1e'&&(snapshot.state.ruleset||'pathfinder-1e')===entry.ruleset&&c.choices?`<button data-library-copy="${esc(entry.id)}" data-library-character="${esc(c.id)}">Crear copia inicial aquí</button>`:''}</div></div>`).join('');
  const summary=entry.characters.length===1?'Personaje · '+esc(entry.characters[0].name):'Personajes · '+entry.characters.length;
  return `<article class="library-entry" data-library-entry="${esc(entry.id)}"><h3>${esc(entry.title)}</h3><small>${esc(entry.playerName)} · ${entry.ruleset==='pathfinder-1e'?'Pathfinder 1e':esc(entry.ruleset)} · ${entry.host?'Anfitrión':'Jugador'}</small><div class="toolbar"><button data-library-open="${esc(entry.id)}">Volver a esta partida</button></div>${entry.characters.length?`<details class="library-characters"><summary>${summary}</summary>${characters}</details>`:''}</article>`;
 }).join('');
}
function renderSavedCampaigns(){
 const target=$('#savedCampaigns');if(!target)return;
 try{
  const library=CampaignLibrary.read(localStorage),panel=$('#savedLibraryPanel'),hasEntries=String(library.entries.length>0);
  target.innerHTML=libraryHtml(library);
  if(panel.dataset.hasEntries!==hasEntries){panel.open=hasEntries==='true';panel.dataset.hasEntries=hasEntries;}
 }
 catch{target.textContent='No se puede leer la biblioteca local. Se conservan sus datos; puedes seguir usando el acceso actual.'}
}
function openCampaignLibrary(){
 const library=CampaignLibrary.read(localStorage);
 modal(`<div class="eyebrow">TUS CRÓNICAS</div><h2>Partidas y personajes</h2><p>Las partidas se guardan en el servidor. Esta lista de accesos pertenece a este perfil del navegador.</p>${libraryHtml(library,!!snapshot&&!$('#app').hidden)}<details id="libraryAccessTools"><summary>Guardar o recuperar mis accesos</summary><p>El archivo permite entrar con tus permisos, incluidos los de anfitrión. Guárdalo en privado; no lo compartas ni lo subas al repositorio.</p><button id="exportAccesses">Guardar mis accesos</button><label>Recuperar accesos desde un archivo<input id="importAccesses" type="file" accept=".json,application/json" aria-describedby="accessImportStatus"></label><p id="accessImportStatus" role="status" aria-live="polite"></p></details>`);
 $('#exportAccesses').onclick=()=>{
  const url=URL.createObjectURL(new Blob([JSON.stringify(CampaignLibrary.read(localStorage))],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='cronicas-accesos-privados.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 };
 const tools=$('#libraryAccessTools'),input=$('#importAccesses'),status=$('#accessImportStatus');let reads=0;
 input.onchange=run(async()=>{
  const read=++reads,file=input.files[0];if(!file)return;
  const current=()=>read===reads&&tools.isConnected&&$('#modal').open&&$('#modal').contains(tools);
  status.textContent='Leyendo tus accesos…';
  try{
   if(file.size>1000000)throw Error('Elige un archivo de accesos de hasta 1 MB.');
   const text=await file.text();if(!current())return;
   let data;try{data=JSON.parse(text)}catch{throw Error('No se puede leer este archivo. Elige una copia de accesos guardada desde «Mis partidas».')}
   CampaignLibrary.merge(localStorage,data);renderSavedCampaigns();openCampaignLibrary();toast('Accesos recuperados. Se comprobarán al abrir cada partida.');
  }catch(error){if(current()){status.textContent=error.message;throw error}}
  finally{if(input.isConnected&&read===reads)input.value=''}
 });
}
document.addEventListener('click',e=>{
 const button=e.target.closest('[data-library-open],[data-library-copy]');if(!button)return;
 run(async()=>{
  if(button.dataset.libraryOpen){button.disabled=true;try{await openSavedCampaign(button.dataset.libraryOpen,button.dataset.libraryCharacter)}finally{if(button.isConnected)button.disabled=false}return}
  if(snapshot.state.board?.active)throw Error('Finaliza el combate antes de crear una copia.');
  const entry=CampaignLibrary.read(localStorage).entries.find(v=>v.id===button.dataset.libraryCopy);
  const character=entry?.characters.find(v=>v.id===button.dataset.libraryCharacter);
  if(!entry||!character)throw Error('Personaje guardado no encontrado');
  const choices=CampaignLibrary.template(entry,character,snapshot.state.ruleset||'pathfinder-1e');
  modal(`<h2>Una nueva copia de ${esc(character.name)}</h2><p>Se recalcula un personaje de nivel 1 con sus elecciones iniciales. El progreso, heridas y cambios de equipo del original permanecen en su campaña.</p><form id="copyLibraryCharacter"><label>Nombre<input name="name" value="${esc(character.name)}" maxlength="80" required></label><button class="primary" aria-describedby="libraryCopyStatus">Crear copia inicial</button><p id="libraryCopyStatus" role="status"></p></form>`);
  const form=$('#copyLibraryCharacter'),access=token,campaign=snapshot.id,player=snapshot.me.id;
  const sameContext=()=>token===access&&snapshot?.id===campaign&&snapshot?.me.id===player;
  const current=()=>sameContext()&&form.isConnected&&$('#modal').open&&$('#modal').contains(form);
  let submitting=false;
  form.onsubmit=run(async()=>{
   if(!current()||submitting)return;
   if(snapshot.state.board.active)throw Error('Finaliza el combate antes de crear una copia.');
   const name=form.elements.name.value.trim();if(!name)throw Error('Escribe un nombre para la copia.');
   const priorIds=new Set(snapshot.state.characters.map(c=>c.id)),controls=[...form.querySelectorAll('input,button')];
   submitting=true;controls.forEach(element=>element.disabled=true);form.querySelector('#libraryCopyStatus').textContent=`Guardando a ${name}. Estará en la mesa aunque cierres esta ventana.`;
   try{
    await act('create_character',{choices:{...choices,name}});
    if(!current()){if(sameContext())toast(`${name}: copia creada y disponible en la mesa`);return}
    const matches=snapshot.state.characters.filter(c=>!priorIds.has(c.id)&&c.owner===player&&c.name===name&&!c.enemy);
    $('#modal').close();
    if(matches.length===1){const created=matches[0];$('#boardCharacter').value=created.id;$('#speaker').value=created.id;renderBoard();characterForm(created.id,true)}
    else toast('Copia creada. Elige su ficha en la mesa.');
   }finally{
    submitting=false;if(current()){controls.forEach(element=>element.disabled=false);form.querySelector('#libraryCopyStatus').textContent='Puedes revisar el nombre. Si hay un envío pendiente, recupéralo antes de crear otra copia.'}
   }
  });
 })(e);
});
