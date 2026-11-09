let libraryWarningShown=false;
function rememberCampaign(){
 try{CampaignLibrary.record(localStorage,snapshot,token);renderSavedCampaigns()}
 catch(error){if(!libraryWarningShown){toast('No se pudo actualizar la lista local de accesos. La campaña sigue guardada en el servidor. '+error.message);libraryWarningShown=true}}
}
function ensureCampaignCanChange(destination){
 const pending=JSON.parse(localStorage.getItem('cronicas-pending')||'null');
 if(busy||(pending&&!(pending.token!==token&&pending.token===destination)))throw Error('Recupera o termina el envío pendiente antes de cambiar de campaña.');
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
 const previousToken=token;let next;
 try{
  token=entry.token;
  next=await api('/api/state');
  if(next.id!==entry.campaign||next.me.id!==entry.player)throw Error('La credencial no coincide con el acceso guardado');
  localStorage.setItem('cronicas-token',token);
 }catch(error){token=previousToken;throw error}
 bookReader.reset();document.body.classList.remove('reader-wide');readerExpanded=false;
 snapshot=next;snapshotToken=token;lastVersion=next.version;path=[];ruler=[];rememberCampaign();renderSyncStatus();render();
 if($('#modal').open)$('#modal').close();
 if(characterId&&next.state.characters.some(c=>c.id===characterId&&c.owner===next.me.id)){
  if(next.state.ruleset==='rule-pack')RulePackUI.openCharacter(characterId);else if(next.state.ruleset==='cairn-1e')CairnUI.openCharacter(characterId);else characterForm(characterId);
 }
}
function libraryHtml(library,inCampaign=false){
 if(!library.entries.length)return '<p>Tus partidas y personajes aparecerán aquí al entrar en una campaña.</p>';
 return library.entries.map(entry=>`<article class="library-entry"><h3>${esc(entry.title)}</h3><small>${esc(entry.playerName)} · ${entry.ruleset==='pathfinder-1e'?'Pathfinder 1e':esc(entry.ruleset)} · ${entry.host?'Anfitrión':'Jugador'}</small><div class="toolbar"><button data-library-open="${esc(entry.id)}">Volver a esta partida</button></div>${entry.characters.map(c=>`<div class="library-character"><strong>${esc(c.name)}</strong><small>${entry.ruleset==='cairn-1e'?'Cairn 1e · '+esc(c.background):esc(c.race)+' · '+esc(c.class)+' '+c.level}</small><div class="toolbar"><button data-library-open="${esc(entry.id)}" data-library-character="${esc(c.id)}">Abrir personaje original</button>${inCampaign&&entry.ruleset==='pathfinder-1e'&&(snapshot.state.ruleset||'pathfinder-1e')===entry.ruleset&&c.choices?`<button data-library-copy="${esc(entry.id)}" data-library-character="${esc(c.id)}">Crear copia inicial aquí</button>`:''}</div></div>`).join('')}</article>`).join('');
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
 modal(`<div class="eyebrow">TUS CRÓNICAS</div><h2>Partidas y personajes</h2><p>Las partidas se guardan en el servidor. Esta lista de accesos pertenece a este perfil del navegador.</p>${libraryHtml(library,!!snapshot&&!$('#app').hidden)}<details><summary>Guardar o recuperar mis accesos</summary><p>El archivo permite entrar con tus permisos, incluidos los de anfitrión. Guárdalo en privado; no lo compartas ni lo subas al repositorio.</p><button id="exportAccesses">Guardar mis accesos</button><label>Recuperar accesos desde un archivo<input id="importAccesses" type="file" accept=".json,application/json"></label></details>`);
 $('#exportAccesses').onclick=()=>{
  const url=URL.createObjectURL(new Blob([JSON.stringify(CampaignLibrary.read(localStorage))],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='cronicas-accesos-privados.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 };
 $('#importAccesses').onchange=run(async e=>{
  const file=e.target.files[0];if(!file||file.size>1000000)throw Error('Elige un archivo de accesos de hasta 1 MB.');
  CampaignLibrary.merge(localStorage,JSON.parse(await file.text()));renderSavedCampaigns();openCampaignLibrary();toast('Accesos recuperados. Se comprobarán al abrir cada partida.');
 });
}
document.addEventListener('click',e=>{
 const button=e.target.closest('[data-library-open],[data-library-copy]');if(!button)return;
 run(async()=>{
  if(button.dataset.libraryOpen){await openSavedCampaign(button.dataset.libraryOpen,button.dataset.libraryCharacter);return}
  if(snapshot.state.board?.active)throw Error('Finaliza el combate antes de crear una copia.');
  const entry=CampaignLibrary.read(localStorage).entries.find(v=>v.id===button.dataset.libraryCopy);
  const character=entry?.characters.find(v=>v.id===button.dataset.libraryCharacter);
  if(!entry||!character)throw Error('Personaje guardado no encontrado');
  const choices=CampaignLibrary.template(entry,character,snapshot.state.ruleset||'pathfinder-1e');
  modal(`<h2>Una nueva copia de ${esc(character.name)}</h2><p>Se recalcula un personaje de nivel 1 con sus elecciones iniciales. El progreso, heridas y cambios de equipo del original permanecen en su campaña.</p><form id="copyLibraryCharacter"><label>Nombre<input name="name" value="${esc(character.name)}" maxlength="80" required></label><button class="primary">Crear copia inicial</button></form>`);
  $('#copyLibraryCharacter').onsubmit=run(async event=>{
   await act('create_character',{choices:{...choices,name:event.target.elements.name.value}});
   $('#modal').close();characterForm(snapshot.state.characters.at(-1).id);
  });
 })(e);
});
