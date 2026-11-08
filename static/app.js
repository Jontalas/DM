const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
let token=localStorage.getItem('cronicas-token'), model={}, snapshot, snapshotToken, path=[], ruler=[], lastVersion=-1, busy=false, toastTimer;
const names={reglas:'Reglas básicas',bestiario:'Bestiario',trey:'TREY'};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const characterIsConscious=c=>!!c&&(c.hp>=0||(c.hp>-c.abilities[2]&&c.stable===true&&c.recoveryState?.conscious===true));
const characterHealthLabel=c=>c.hp<=-c.abilities[2]?'Ha muerto':c.hp>0?'':characterIsConscious(c)?'Incapacitado':c.stable===true?'Inconsciente y estable':'Moribundo';
const characterMovementCells=c=>c&&characterIsConscious(c)&&Number.isInteger(c.speed)?Math.floor(c.speed/(c.hp<=0?2:1)):0;
const boardCharacters=s=>s.boardScenes?s.characters.filter(c=>c.sceneId===s.boardScenes.current):s.characters;
function toast(s){$('#toast').textContent=s;$('#toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').hidden=true,7000)}
async function api(url,body){
 let response;
 try{response=await fetch(url,{method:body?'POST':'GET',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:body?JSON.stringify(body):undefined})}
 catch{throw Error('No se pudo conectar con la mesa. Vuelve a intentarlo cuando tengas conexión.')}
 let data;
 try{data=await response.json()}
 catch{throw Error('La mesa no devolvió una respuesta válida. Vuelve a intentarlo.')}
 if(!response.ok){const error=Error(data?.error||'Error del servidor');error.confirmed=response.status>=400&&response.status<500;error.status=response.status;throw error}
 return data;
}
function values(form){return Object.fromEntries(new FormData(form))}
function physical(d){if(d.physical?.trim())d.physical=d.physical.split(',').map(Number);else delete d.physical;return d}
async function recoverSubmission(saved){
 try{await api('/api/action',saved.body)}catch(error){
  if(error.status!==409||saved.body.type!=='resolve_pack_request')throw error;
  await refresh(true);
  const pending=snapshot?.state.narrativeView?.pending;
  if(pending?.id!==saved.body.request||pending.randomnessScope!=='pending-resolution-v2')throw error;
  const body={...saved.body,id:crypto.randomUUID(),version:snapshot.version};
  localStorage.setItem('cronicas-pending',JSON.stringify({token,body}));
  await api('/api/action',body);
 }
}
async function act(type,data={}){if(JSON.parse(localStorage.getItem('cronicas-pending')||'null')?.token===token)throw Error('Recarga la mesa para recuperar el envio pendiente antes de otra accion');if(busy)throw Error('Hay una acción en curso');busy=true;$('#send').disabled=true;$('#sync').textContent='Resolviendo…';const body={...data,type,id:crypto.randomUUID(),version:snapshot.version};if((!snapshot.state.ruleset||snapshot.state.ruleset==='pathfinder-1e')&&['talk','start_adventure','continue_adventure'].includes(type))body.captureContract='pf-director-action-1';try{localStorage.setItem('cronicas-pending',JSON.stringify({token,body}));await api('/api/action',body);localStorage.removeItem('cronicas-pending');path=[];await refresh(true)}catch(e){if(e.name==='QuotaExceededError')throw Error('No hay espacio en el navegador para conservar este envio. No se ha enviado al servidor; libera espacio o importa una copia mas pequena.');if(e.confirmed)localStorage.removeItem('cronicas-pending');try{await refresh(true)}catch{}throw e}finally{busy=false;renderComposerAvailability()}}
function run(fn){return async e=>{e?.preventDefault();try{await fn(e)}catch(err){toast(err.message)}}}
async function refresh(force=false){
 if(!token)return;
 const requestedToken=token,previous=snapshot,params=new URLSearchParams();
 if(!force&&previous&&snapshotToken===requestedToken)params.set('version',previous.version);
 const cached=previous?.me.host&&snapshotToken===requestedToken&&previous.state.authoringWorkspace&&previous.state.authoringWorkspaceRef?.sha256;
 if(cached)params.set('workspace',cached);
 const next=await api('/api/state'+(params.size?'?'+params:''));
 if(token!==requestedToken)return;
 if(next.unchanged){$('#sync').textContent='Guardado en Firebase';return}
 if(next.workspaceUnchanged){
  if(!cached||next.workspaceUnchanged!==cached||next.id!==previous.id||next.me.id!==previous.me.id||!next.me.host)throw Error('La caché privada no corresponde a este acceso; recarga para recuperarla.');
  next.state.authoringWorkspace=previous.state.authoringWorkspace;
 }
 if(previous?.state.boardScenes?.current!==next.state.boardScenes?.current){path=[];ruler=[];}
 snapshot=next;snapshotToken=requestedToken;rememberCampaign();$('#sync').textContent='● Guardado en Firebase';
 if(!force&&lastVersion===next.version)return;lastVersion=next.version;render();
}
function chooseTab(id,loadDocument=true){if(id==='board'&&window.matchMedia('(min-width:1100px)').matches)id='story';$$('.tab').forEach(x=>x.classList.toggle('active',x.id===id));$$('[data-tab]').forEach(x=>x.classList.toggle('active',x.dataset.tab===id));document.body.classList.toggle('reader-wide',id==='books'&&readerExpanded);if(id==='books'&&loadDocument)openBook();}
function ref(book,page,label){return `<button type="button" class="rule-link" data-book="${esc(book)}" data-page="${Number(page)}">${esc(label||names[book]+' · PDF p.'+page)} ↗</button>`}
function renderSpeakerChoices(){
 if(!snapshot)return;
 const me=snapshot.me,kind=$('#messageKind').value,previous=$('#speaker').value;
 const choices=snapshot.state.characters.filter(c=>c.owner===me.id||(me.host&&(c.enemy||['ooc','private'].includes(kind))));
 $('#speaker').innerHTML='<option value="">'+esc(me.name)+'</option>'+choices.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('');
 if(choices.some(c=>c.id===previous))$('#speaker').value=previous;
 renderComposerAvailability();
}
function conversationUnavailable(){
 if(!snapshot||!['action','dialogue'].includes($('#messageKind').value)||(snapshot.state.ruleset&&snapshot.state.ruleset!=='pathfinder-1e'))return '';
 const cid=$('#speaker').value,actors=cid?snapshot.state.characters.filter(c=>c.id===cid):snapshot.state.characters.filter(c=>c.owner===snapshot.me.id&&!c.enemy);
 return actors.length&&!actors.some(characterIsConscious)?'La ficha está inconsciente o muerta y no puede actuar ni hablar. Puedes elegir «Fuera de personaje» o «Nota privada».':'';
}
function renderComposerAvailability(){
 if(!snapshot)return;
 const reason=conversationUnavailable();$('#send').disabled=busy||!!reason;
 $('#message').setAttribute('aria-describedby','aiHint');
 $('#aiHint').textContent=reason||(model.aiConfigured?'El director responderá si activas «Responder con IA». Las tiradas y herramientas funcionan sin IA.':'El director no está disponible en esta mesa. Puedes usar las fichas, los dados y el tablero sin IA.');
}
async function recoverPendingSubmission(){
 if(busy)throw Error('Hay una acción en curso');
 const saved=JSON.parse(localStorage.getItem('cronicas-pending')||'null');
 if(!saved||saved.token!==token)throw Error('No hay un envío pendiente de esta partida');
 busy=true;$('#send').disabled=true;$('#playGuidanceAction').disabled=true;$('#sync').textContent='Recuperando envío…';
 try{await recoverSubmission(saved);localStorage.removeItem('cronicas-pending');if(saved.body.type==='talk'&&$('#message').value===saved.body.text)$('#message').value='';toast('Envío recuperado')}
 catch(error){if(error.confirmed)localStorage.removeItem('cronicas-pending');throw error}
 finally{try{await refresh(true)}catch{}busy=false;renderComposerAvailability();$('#playGuidanceAction').disabled=false}
}
function renderPlayGuidance(s){
 const panel=$('#playGuidance'),text=$('#playGuidanceText'),button=$('#playGuidanceAction');
 const checks=s.pending.filter(p=>p.check),mine=checks.filter(p=>s.characters.some(c=>c.id===p.check.character&&c.owner===snapshot.me.id)),own=mine.filter(p=>!pendingCheckUnavailable(p,s.characters.find(c=>c.id===p.check.character)));
 let message='',label='',open;
 const saved=JSON.parse(localStorage.getItem('cronicas-pending')||'null');
 if(saved?.token===token){
  message='Tu último envío aún no está confirmado. Recupéralo antes de continuar.';
  label='Recuperar envío';open=run(recoverPendingSubmission);
 }else if(own.length){
  message=own.length===1?'Tienes una tirada pendiente. Resuélvela para continuar.':`Tienes ${own.length} tiradas pendientes. Puedes resolverlas en la conversación.`;
  label='Ver mi tirada';
  open=()=>{const target=$$('[data-resolve-check]').find(b=>b.dataset.resolveCheck===own[0].check.id);if(target){target.scrollIntoView({block:'center'});target.focus({preventScroll:true})}};
 }else if(mine.length){
  message='Una tirada pendiente requiere revisar el estado de tu personaje.';
  label='Revisar mi personaje';open=()=>characterForm(mine[0].check.character);
 }else if(checks.length){
  message='Hay tiradas pendientes. Cada jugador puede revisar las que corresponden a su personaje.';
  label='Ver tiradas';open=()=>$('#checkRequests').scrollIntoView({block:'center'});
 }else if(s.board.active&&s.pfCeasefireView?.reason===null&&s.characters.some(c=>c.id===s.pfEncounter?.character&&c.owner===snapshot.me.id)){
  message='La guardiana ofrece detener el combate. Puedes aceptar la tregua o seguir luchando.';
  label='Ver la tregua';open=()=>{chooseTab('story');const target=$('#pfAcceptCeasefire');target?.scrollIntoView({block:'center'});target?.focus({preventScroll:true})};
 }else if(s.board.active){
  const current=s.characters.find(c=>c.id===s.board.order[s.board.turn]?.id);
  message=s.board.autoPaused?'Un turno automático necesita revisión. Consulta el aviso de la mesa.':current?.owner===snapshot.me.id?(characterIsConscious(current)?'Es tu turno. Elige tu acción en el tablero.':'Tu personaje no puede actuar. Revisa su estado en la mesa.'):`Es el turno de ${current?.name||'otro participante'}. Puedes consultar la mesa mientras tanto.`;
  label='Ver el tablero';open=()=>{chooseTab('board');if(current?.owner===snapshot.me.id){$('#boardCharacter').value=current.id;path=[];renderBoard()}$('#board').scrollIntoView({block:'start'});$('#boardCharacter').focus({preventScroll:true})};
 }else if(s.pending.length){
  message=snapshot.me.host?'Hay una situación pendiente de resolución excepcional. Puedes revisarla en el diario.':'El anfitrión tiene una situación pendiente de resolución excepcional.';
  label='Ver pendientes';open=()=>{chooseTab('journal');$('#journalPending').scrollIntoView({block:'center'})};
 }else if(s.adventureRouteView?.exits.length&&(s.adventureModuleView?.completed||s.adventureRouteView.completed)){
  message=s.adventureRouteView.completed?'Has resuelto el objetivo de la ruta. Puedes volver a los lugares conocidos; tus hallazgos se conservan.':'La investigación de este lugar está resuelta. Puedes consultar las salidas de la ruta.';
  label='Ver salidas';open=()=>{const exits=$$('[data-route-exit]');$('#investigationPanel').scrollIntoView({block:'start'});exits.find(b=>!b.disabled)?.focus({preventScroll:true})};
 }else if(s.adventureRouteView?.completed){
  message='Has completado la ruta preparada. Puedes revisar los hallazgos en el diario; otros viajes aún no están disponibles.';
  label='Revisar el diario';open=()=>chooseTab('journal');
 }else if(s.adventureModuleView?.completed){
  message='La investigación está resuelta. Puedes revisar lo descubierto y decidir tu siguiente acción.';
  label='Revisar el diario';open=()=>chooseTab('journal');
 }
 panel.hidden=!message;
 if(text.textContent!==message)text.textContent=message;
 if(button.textContent!==label)button.textContent=label;
 button.onclick=open||null;
}
function renderJournalOverview(s){
 const lists=[['Aliados',s.allies],['Enemigos',s.enemies],['Incógnitas',s.unknowns]].filter(([,items])=>items?.length);
 const unmeasuredActivity=s.adventureRouteView?.visits>1||s.adventureModuleView?.searchActions>0;
 const knownAnchor=['Comienzo de la aventura','Inicio de la noche del patio'].includes(s.worldTime)||(s.pfNightRestView?.completed&&s.worldTime===s.pfNightRestView.result?.worldTimeAfter);
 const unknownCurrentTime=s.boardScenes&&unmeasuredActivity&&knownAnchor;
 const timeLabel=unknownCurrentTime?'Hora no registrada':s.worldTime;
 const resolved=s.adventureRouteView?.completed?'Ruta completada':!s.adventureRouteView&&s.adventureModuleView?.completed?'Investigación resuelta':'';
 $('#journalOverview').innerHTML=`<h3>Situación actual</h3><p><strong>${esc(s.location)}</strong> · ${esc(timeLabel)}</p><p>${esc(s.goal)}</p>${resolved?`<p class="notice">${esc(resolved)}. Los hallazgos confirmados quedan guardados.</p>`:''}${!s.adventure&&s.objectives.length?`<ul>${s.objectives.map(v=>`<li>${esc(v)}</li>`).join('')}</ul>`:''}${s.notes?`<h4>Notas confirmadas</h4><p>${esc(s.notes)}</p>`:''}${s.adventureRouteView?.visitedScenes?.length>1?`<details class="visited-scene-notes"><summary>Lugares visitados y hallazgos</summary>${s.adventureRouteView.visitedScenes.map(v=>`<h4>${esc(v.location)}</h4>${v.discoveries.length?v.discoveries.map(d=>`<p>${esc(d.text)}</p>`).join(''):'<p>Sin hallazgos confirmados todavía.</p>'}`).join('')}</details>`:''}${lists.length?`<details><summary>Personas e incógnitas</summary>${lists.map(([title,items])=>`<h4>${title}</h4><ul>${items.map(v=>`<li>${esc(v)}</li>`).join('')}</ul>`).join('')}</details>`:''}`;
 $('#journalFacts').hidden=!Object.keys(s.facts).length;
 if(unknownCurrentTime)$('#journalOverview').insertAdjacentHTML('beforeend',`<details class="clock-reference"><summary>Última referencia de tiempo</summary><p>${esc(s.worldTime)}</p><p>La duración de las búsquedas y los trayectos todavía no se calcula. Se conserva esta referencia sin inventar una hora actual.</p></details>`);
 $('#journalConsequences').hidden=!s.consequences.length;
 $('#journalPending').hidden=!s.pending.length;
}
function checkMessage(message){
 const c=message.check;
 if(message.kind!=='rules'||!c||!['ability','save','skill'].includes(c.kind)||typeof c.name!=='string'||!Number.isFinite(c.total)||!Number.isFinite(c.modifier)||!Number.isFinite(c.die))return esc(message.text);
 const character=snapshot.state.characters.find(v=>v.id===c.character),hasDc=Number.isFinite(c.dc)&&typeof c.success==='boolean';
 const outcome=hasDc?(c.success?'Éxito':'Fallo'):'Tirada libre';
 return `<p class="check-result"><strong>${esc(outcome)} · ${esc(character?.name||'Personaje')} · ${esc(c.name)}</strong><br>Total ${esc(c.total)}${hasDc?` contra CD ${esc(c.dc)}`:''}${c.natural?` · ${esc(c.natural)}`:''}</p><details class="check-audit"><summary>Ver cálculo y resultado</summary><p>${esc(message.text)}</p></details>`;
}
function messageSources(message){
 if(!Array.isArray(message.refs)||!message.refs.length)return '';
 const links=message.refs.map(r=>ref(r.book,r.page)).join('');
 return message.kind==='director'?`<details class="message-sources"><summary>Consultar fuentes</summary><div>${links}</div></details>`:`<div>${links}</div>`;
}
function recoveryAudit(message){
 if(!Array.isArray(message.recoveryChecks)||!message.recoveryChecks.length||message.recoveryChecks.length>40||message.recoveryChecks.some(check=>!check||typeof check!=='object'))return '';
 return `<details class="recovery-audit"><summary>Ver tiradas de recuperación (${message.recoveryChecks.length})</summary>${message.recoveryChecks.map((check,i)=>`<p>${check.characterName?esc(check.characterName)+' · hora '+esc(check.hour):'Hora '+(i+1)}: d20 ${esc(check.die)}, modificador ${esc(check.modifier)}, total ${esc(check.total)} frente a 10. ${check.conscious?'Recupera la consciencia':check.dead?'Muere por sus heridas':'Sigue inconsciente'}. PG: ${esc(check.hpBefore)} → ${esc(check.hpAfter)}.</p>`).join('')}</details>`;
}
function render(){if(snapshot.state.ruleset==='rule-pack'){RulePackUI.render();return}if($('#rulePackWorkspace'))$('#rulePackWorkspace').hidden=true;if(snapshot.state.ruleset==='cairn-1e'){$('#campaignTitle').textContent=snapshot.title;$('#campaignMeta').textContent='Cairn 1e';$('#inviteBtn').hidden=!snapshot.me.host;$('#welcome').hidden=true;$('#app').hidden=false;$('#app > .workspace').hidden=true;run(()=>CairnUI.render())();return}if($('#systemWorkspace'))$('#systemWorkspace').hidden=true;$('#app > .workspace').hidden=false;const s=snapshot.state, me=snapshot.me;$('#savedLibraryPanel').hidden=true;$('#welcome').hidden=true;$('#app').hidden=false;$('#campaignTitle').textContent=snapshot.title;$('#campaignMeta').textContent=`Pathfinder 1e · ${snapshot.players.length} jugadores · ${s.characters.length} personajes`;$('#place').textContent=s.location;$('#objective').textContent=s.goal;$('#sceneNum').textContent=s.scene;$('#tokenNum').textContent=`${s.tokens} / ${s.threshold}`;$('#phase').textContent=s.turned?'Punto de giro alcanzado · desenlace':'Desarrollo de la aventura';$('#sceneTitle').textContent=`Escena ${s.scene} · ${s.location}`;
 $('#party').innerHTML=s.characters.map(c=>`<div class="party-person" role="button" tabindex="0" data-character="${esc(c.id)}"><div class="avatar">${esc(c.name[0])}</div><div><strong>${esc(c.name)}</strong><small>${esc(c.race)} · ${esc(c.class)} ${c.level}</small><div class="hpbar"><span style="width:${Math.max(0,Math.min(100,100*c.hp/c.maxHp))}%"></span></div><small>${c.hp} / ${c.maxHp} PG${characterHealthLabel(c)?' · '+esc(characterHealthLabel(c)):''} · ${esc(c.npcCreation?'Director de la aventura':snapshot.players.find(p=>p.id===c.owner)?.name||'Jugador anterior')}${s.boardScenes&&c.sceneId!==s.boardScenes.current?' · En otra escena':''}</small></div></div>`).join('')||'<small>Aún no hay personajes. Crea tu primer aventurero.</small>';
 const available=s.characters.filter(c=>me.host||c.owner===me.id), boardPrev=$('#boardCharacter').value;
 renderSpeakerChoices();
 const boardAvailable=boardCharacters(s).filter(c=>me.host||c.owner===me.id);
 $('#boardCharacter').innerHTML=boardAvailable.map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join('');if(boardAvailable.some(c=>c.id===boardPrev))$('#boardCharacter').value=boardPrev;
 const area=$('#story'), near=area.scrollHeight-area.scrollTop-area.clientHeight<150;
 $('#messages').innerHTML=s.messages.map(m=>`<article class="message ${esc(m.kind)}"><div class="speaker">${esc(m.speaker)} · ${esc({rules:'Resolución',director:'Director de IA',action:'Acción',dialogue:'Diálogo',ooc:'Fuera de personaje',private:'Privado'}[m.kind]||m.kind)}</div>${checkMessage(m)}${recoveryAudit(m)}${messageSources(m)}</article>`).join('')||`<div class="empty"><div class="icon">✧</div><h3>Una página todavía en blanco</h3><p>Crea un personaje y presenta la situación inicial.<br>${model.aiConfigured?'El director está configurado; su disponibilidad se comprobará al enviar.':'Puedes crear tu personaje, consultar libros y usar el tablero. El director no está disponible en esta mesa.'}</p></div>`;
 if(!available.length)$('#messages').insertAdjacentHTML('afterbegin','<div class="card"><h3>Tu personaje es el primer paso</h3><p>Elige sus opciones; el creador calcula la ficha y la deja lista para jugar.</p><button class="primary" data-create-hero>Crear mi personaje</button></div>');
 renderAdventure();renderChecks();renderPlayGuidance(s);if(near)area.scrollTop=area.scrollHeight;
 renderJournalOverview(s);
 const jf=$('#journalForm');for(const key of ['location','worldTime','goal','notes','secrets','directorNotes','objectives','allies','enemies','unknowns']){const el=jf.elements[key];if(document.activeElement!==el)el.value=Array.isArray(s[key])?s[key].join('\n'):s[key]||'';el.disabled=!me.host}
 $$('.host-only').forEach(x=>x.hidden=!me.host);$('#inviteBtn').hidden=!me.host;$('#exportBtn').disabled=!me.host;
 $('#facts').innerHTML=Object.entries(s.facts).map(([k,v])=>`<p>${esc(k)} · <strong>${esc(v.answer)}</strong><small>${esc(v.interpretation)}</small></p>`).join('')||'<small>Sin hechos establecidos mediante el oráculo.</small>';
 $('#consequences').innerHTML=s.consequences.map(v=>`<p>${esc(v.outcome)} · ${esc(v.target)} · ${esc(v.when)}<small>d10/d8/d6 ${esc(v.raw.join('/'))} · ${v.interpreted?'Interpretación registrada.':'Pendiente de interpretar en las notas.'}</small>${ref('trey',v.page)}</p>`).join('')||'<small>Ninguna.</small>';
 $('#pending').innerHTML=s.pending.map((v,i)=>`<p>${esc(v.reason)}<small>${esc(v.source)}</small>${v.check?'<button data-tab="story">Ver tirada solicitada</button>':`<button data-pending="${i}">Resolver manualmente</button>`}</p>`).join('')||'<small>Sin propuestas pendientes.</small>';
 $('#criteria').innerHTML='<p>'+esc(s.agreement)+'</p>'+s.criteria.map(v=>'<p>'+esc(v)+'</p>').join('');
 $('#oracleLog').innerHTML=s.oracleLog.map(v=>`<p>${esc(v.question)} · ${esc(v.result)}<small>Escena ${v.scene} · ${esc(v.origin)} · originales ${esc(v.raw.join('/'))} · ${esc(v.probability)} → ${v.total} · ${esc(v.group)} d8=${v.detail??'no aplica'}<br>${esc(v.interpretation)}</small>${ref('trey',19)}</p>`).join('')||'<small>No se ha consultado el oráculo.</small>';
 $('#bookmarks').innerHTML=s.bookmarks.map(v=>ref(v.book,v.page,v.label)).join('');renderBoard();
}
function renderBoard(){if(!snapshot)return;renderAttack();renderAutomation();const s=snapshot.state,board=s.board;const title=s.boardScenes?s.location:'Mesa táctica';if($('#board h2').textContent!==title)$('#board h2').textContent=title;$('#turnInfo').textContent=board.active?`Asalto ${board.round} · Turno de ${s.characters.find(c=>c.id===board.order[board.turn].id)?.name} · ${board.order.map(o=>s.characters.find(c=>c.id===o.id)?.name+' '+(o.roll+o.modifier)).join(' → ')}`:'Exploración · sin combate activo';
 let cells='';for(let y=0;y<20;y++)for(let x=0;x<20;x++){const c=boardCharacters(s).find(c=>c.x===x&&c.y===y);cells+=`<button class="cell ${board.terrain[x+','+y]||''} ${path.some(p=>p[0]===x&&p[1]===y)?'path':''} ${ruler.some(p=>p[0]===x&&p[1]===y)?'measured':''} ${c&&board.active&&board.order[board.turn]?.id===c.id?'current-turn':''}" data-token-id="${esc(c?.id||'')}" data-controlled="${!!c&&(snapshot.me.host||c.owner===snapshot.me.id)}" aria-pressed="${!!c&&c.id===$('#boardCharacter').value}" data-x="${x}" data-y="${y}" aria-label="Casilla ${x},${y}${c?' '+esc(c.name):''}">${c?`<span class="token ${c.enemy?'enemy':''}">${esc(c.name.slice(0,2))}</span><span class="token-hp">${c.hp} PG</span>`:''}</button>`}$('#grid').innerHTML=cells;
 let c=s.characters.find(c=>c.id===$('#boardCharacter').value),x=c?.x,y=c?.y,diagonal=0,cost=0;for(const [nx,ny] of path){let d=nx!==x&&ny!==y;if(d)diagonal++;cost+=board.terrain[nx+','+ny]==='difficult'?(d?3:2):(d&&diagonal%2===0?2:1);x=nx;y=ny}$('#pathInfo').textContent=path.length?`Recorrido: ${path.map(p=>p.join(',')).join(' → ')} · Coste: ${cost*5} pies (${cost} casillas). Revisión manual de AdO, alcance, visibilidad y consecuencias antes de confirmar.`:'Selecciona una ficha y traza casillas adyacentes.';renderTabletopTools()}
function openBook(book=$('#book').value,page=Number($('#page').value)){if(!token)return;$('#book').value=book;$('#page').value=page;bookReader.open(book,page)}
function renderTabletopTools(){
 const board=snapshot.state.board,selected=$('#boardCharacter').value,spent=board.spent[selected]||{};
 const moving=snapshot.state.characters.find(c=>c.id===selected),incapacitated=moving?.hp<=0&&characterIsConscious(moving);
 $('#actionBudget').textContent=board.active?(incapacitated?`Incapacitado · ${spent.standard||spent.move?'Acción usada':'Elige una acción estándar o de movimiento'} · Hasta ${characterMovementCells(moving)} casillas completas por movimiento`:`Estándar: ${spent.standard?'gastada':'disponible'} · Movimiento: ${spent.move?'gastado':'disponible'}`):'Exploración';
 const measuring=$('#tool').value==='measure';
 $('.board-scroll').dataset.tool=$('#tool').value;
 $('#confirmMove').disabled=measuring||$('#tool').value==='pan'||!path.length;
 let movementReason='';
 if(moving?.hp<=0&&path.length&&!measuring&&$('#tool').value==='move'){
  let x=moving.x,y=moving.y,diagonal=0,cost=0;
  for(const [nx,ny] of path){const d=nx!==x&&ny!==y;if(d)diagonal++;cost+=board.terrain[nx+','+ny]==='difficult'?(d?3:2):(d&&diagonal%2===0?2:1);x=nx;y=ny}
  movementReason=!characterIsConscious(moving)?'No puede moverse en su estado actual. Revisa su ficha.':board.active&&board.order[board.turn]?.id!==moving.id?'Espera al turno de esta ficha.':board.active&&(spent.standard||spent.move)?'Incapacitado: ya has usado tu acción de este turno.':board.active&&cost>characterMovementCells(moving)?`Este recorrido supera las ${characterMovementCells(moving)} casillas completas de tu movimiento reducido.`:'';
  if(movementReason)$('#confirmMove').disabled=true;
  $('#pathInfo').textContent+=(incapacitated?' Incapacitado: velocidad reducida a la mitad.':'')+(movementReason?' '+movementReason:'');
 }
 $('#confirmMove').hidden=!path.length||$('#tool').value!=='move';
 $('#clearPath').hidden=!path.length;
 if($('#tool').value==='pan')$('#pathInfo').textContent='Arrastra el mapa para desplazar la vista. También puedes usar el botón derecho.';
 if(measuring){
  if(ruler.length===2){const dx=Math.abs(ruler[1][0]-ruler[0][0]),dy=Math.abs(ruler[1][1]-ruler[0][1]);const d=Math.min(dx,dy);$('#pathInfo').textContent=`Distancia geométrica: ${(Math.max(dx,dy)+Math.floor(d/2))*5} pies. No incluye obstáculos ni terreno difícil.`}
  else $('#pathInfo').textContent=ruler.length?'Origen marcado. Pulsa el destino para medir.':'Pulsa origen y destino para medir sin mover fichas.';
  if(ruler.length===2){
   const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.classList.add('ruler-overlay');svg.setAttribute('aria-hidden','true');
   const cell=$('#grid').firstElementChild.getBoundingClientRect().width,step=cell+1;
   const line=document.createElementNS(svg.namespaceURI,'line');
   for(const [i,point] of ruler.entries()){line.setAttribute('x'+(i+1),point[0]*step+cell/2);line.setAttribute('y'+(i+1),point[1]*step+cell/2)}
   svg.append(line);$('#grid').append(svg);
  }
 }
 for(const option of $('#tool').options)option.disabled=!snapshot.me.host&&['wall','difficult','clear'].includes(option.value);
 $('#startCombat').hidden=!snapshot.me.host||board.active||snapshot.state.pfEncounter?.phase==='offered';
 $('#startCombat').disabled=boardCharacters(snapshot.state).length<2;
 $('#endCombat').hidden=!snapshot.me.host||!board.active;
 $('#manualBtn').hidden=!snapshot.me.host;
 $('#autoEnemies').closest('label').hidden=!snapshot.me.host;
 const current=board.active&&snapshot.state.characters.find(c=>c.id===board.order[board.turn]?.id);
 $('#nextTurn').hidden=!board.active;
 $('#nextTurn').disabled=!current||(!snapshot.me.host&&current.owner!==snapshot.me.id);
 const mine=current&&(snapshot.me.host||current.owner===snapshot.me.id);
 const guidance=!snapshot.state.characters.length?'Usa «Crear personaje» para empezar.':!board.active?'Puedes consultar el mapa, medir o preparar un recorrido. El combate solo empieza cuando lo decides.':!mine?`Es el turno de ${current?.name||'otro participante'}. Puedes consultar el mapa mientras esperas.`:current.id!==selected?`Es el turno de ${current.name}. Selecciona su ficha para actuar.`:(spent.standard&&spent.move||current.hp<=0&&(spent.standard||spent.move))?'Ya has usado tus acciones disponibles. Pulsa «Terminar turno» cuando quieras continuar.':spent.standard?'Ya has usado tu acción estándar. Puedes moverte o terminar el turno.':spent.move?'Ya te has movido. Puedes atacar a un objetivo cercano o terminar el turno.':'Es tu turno. Puedes preparar un movimiento, elegir un objetivo para atacar o terminar el turno.';
 if($('#boardGuidance').textContent!==guidance)$('#boardGuidance').textContent=guidance;
}
$('#requestCheck').onclick=requestCheckForm;
$('#tool').onchange=()=>{path=[];ruler=[];renderBoard()};
$('#quickDice').onclick=run(async e=>{const button=e.target.closest('[data-quick-die]');if(!button)return;const sides=Number(button.dataset.quickDie);await act('roll',{n:1,sides,modifier:0,label:'Tirada rápida d'+sides,source:'Sin modificadores',visibility:'public'})});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('.party-person')){e.preventDefault();characterForm(e.target.dataset.character)}});
window.matchMedia('(min-width:1100px)').addEventListener('change',e=>{if(e.matches&&$('#board').classList.contains('active'))chooseTab('story')});
function renderAutomation(){
 const board=snapshot.state.board,host=!!snapshot.me.host;
 $('#autoEnemies').disabled=!host;
 if(board.active)$('#autoEnemies').checked=!!board.autoEnemies;
 $('#automationNotice').hidden=!board.autoPaused;
 $('#automationNotice').textContent=board.autoPaused?'Turno automático pausado: '+board.autoPaused.reason:'';
 $('#resumeEnemies').hidden=!host||!board.active||!board.autoEnemies||!board.autoPaused;
}
$('#autoEnemies').onchange=run(async()=>{if(snapshot.state.board.active)await act('automation',{enabled:$('#autoEnemies').checked})});
$('#resumeEnemies').onclick=run(()=>act('automation',{enabled:true}));
function meleeFields(c){const p=c.meleeProfile||{flatAc:c.ac,criticalMin:20,multiplier:2};return `<fieldset><legend>Ataque cuerpo a cuerpo automático</legend><label class="check"><input type="checkbox" name="basicMelee" ${c.meleeProfile?'checked':''}> Arma empuñada de alcance 5 pies, daño letal simple; sin aptitudes, resistencia ni ocultación especiales</label><p class="hint">Prepara una vez los totales de ataque y daño de esta arma, incluido su modificador. Se aplicarán automáticamente durante el combate. Perfil para criaturas de una casilla; usa una resolución excepcional para otros casos.</p><div class="row"><label>CA desprevenido<input type="number" name="flatAc" min="0" value="${Number(p.flatAc)}" required></label><label>Amenaza desde d20<select name="criticalMin">${[20,19,18].map(n=>`<option ${n===p.criticalMin?'selected':''}>${n}</option>`).join('')}</select></label><label>Multiplicador crítico<select name="multiplier">${[2,3,4].map(n=>`<option ${n===p.multiplier?'selected':''}>${n}</option>`).join('')}</select></label></div></fieldset>`}
function renderAttack(){
 const s=snapshot.state,board=s.board,selected=$('#boardCharacter').value;
 const source=s.characters.find(c=>c.id===selected),previous=$('#attackTarget').value;
 const targets=boardCharacters(s).filter(c=>source&&c.enemy!==source.enemy&&c.hp>0);
 $('#attackTarget').innerHTML=targets.map(c=>`<option value="${esc(c.id)}">${esc(c.name)} · ${c.hp} PG</option>`).join('');
 if(targets.some(c=>c.id===previous))$('#attackTarget').value=previous;
 const current=board.active&&board.order[board.turn]?.id===selected;
 const spent=board.spent[selected]||{};
 const target=targets.find(c=>c.id===$('#attackTarget').value),adjacent=source&&target&&Math.max(Math.abs(source.x-target.x),Math.abs(source.y-target.y))===1;
 const disabledMove=source?.hp<=0&&spent.move;
 $('#attackForm').hidden=!board.active;
 $('#attackButton').disabled=!current||!source?.meleeProfile||!characterIsConscious(source)||spent.standard||disabledMove||!adjacent;
 $('#attackButton').textContent=source?.hp<=0&&characterIsConscious(source)?'Atacar · perderás 1 PG':'Tirar ataque y resolver';
 $('#attackHint').textContent=!board.active?'El ataque estará disponible durante un combate.':!current?'Selecciona el personaje de tu turno.':!characterIsConscious(source)?'Tu personaje no puede atacar mientras está inconsciente.':!source?.meleeProfile?'El arma necesita un perfil preparado antes del combate.':spent.standard?'Ya has atacado o usado tu acción estándar. Puedes terminar el turno.':disabledMove?'Estás incapacitado y ya te has movido; termina el turno.':!targets.length?'No hay un adversario consciente disponible para este ataque básico.':!adjacent?'Acércate a una casilla junto al objetivo para atacar cuerpo a cuerpo.':source.hp<=0?'Si atacas, perderás 1 PG al terminar y '+(source.hp-1<=-source.abilities[2]?'morirás por tus heridas.':'volverás a quedar moribundo. El movimiento no causa esa pérdida de PG.'):'El juego tira, calcula el impacto y aplica el daño. No tienes que calcular modificadores.';
}
$('#attackTarget').onchange=renderAttack;
$('#attackForm').onsubmit=run(async()=>{await act('attack',{character:$('#boardCharacter').value,target:$('#attackTarget').value})});
function modal(html){$('#modalContent').innerHTML=html;$('#modal').showModal()}
function npcProvenance(character){
 const source=character.npcCreation;if(!source)return '';
 return `<section class="notice" data-npc-provenance><h3>PNJ de la aventura</h3><p>${source.manualOverride?'Esta ficha contiene una corrección excepcional; sus totales actuales ya no se presentan como reproducción automática de la plantilla.':'Estadísticas preparadas desde el Bestiario, con perfil parcial de espada corta. Guardar cambios manuales registrará una corrección excepcional.'}</p><p>Pendiente: ${source.coverage.pending.map(esc).join('; ')}.</p>${source.sources.map(item=>ref(item.book,item.pdfPage,'Consultar fuente · PDF '+item.pdfPage)).join(' ')}<p><a href="/licenses/NPC-CONTENT.md" target="_blank" rel="noopener">Licencia y avisos de las fuentes</a> · <a href="/licenses/OGL-1.0a-Bestiary.txt" target="_blank" rel="noopener">OGL y avisos · Bestiario</a> · <a href="/licenses/OGL-1.0a-Core-Rulebook.txt" target="_blank" rel="noopener">OGL y avisos · Reglas básicas</a></p></section>`;
}
function manualCharacterForm(cid){const c=snapshot.state.characters.find(v=>v.id===cid)||{name:'',race:'Humano',class:'',level:1,abilities:[10,10,10,10,10,10],maxHp:10,hp:10,ac:10,speed:6,initiative:0,attack:0,damage:'1d6',saves:[0,0,0],owner:snapshot.me.id};
 const field=(key,label,value=c[key]||'',type='text')=>`<label>${label}<input name="${key}" type="${type}" value="${esc(value)}"></label>`;
 modal(`<div class="eyebrow">FICHA DE PATHFINDER 1e</div><h2>${c.npcCreation?'PNJ de la aventura':cid?'Tu personaje':'Forja un aventurero'}</h2><p class="hint">Entrada guiada manual. No se certifican opciones de clase, progresión, carga ni dotes. Verifica cada elección en el manual.</p>${cid?sheetChecks(c):''}${npcProvenance(c)}<form id="characterForm"><div class="row">${field('name','Nombre')}${field('race','Raza')}</div><div class="row">${field('class','Clase')}${field('level','Nivel',c.level,'number')}</div><label>Jugador propietario<select name="owner">${c.npcCreation?'<option value="director" selected>Director de la aventura</option>':''}${snapshot.players.map(p=>`<option value="${p.id}" ${p.id===c.owner?'selected':''}>${esc(p.name)}</option>`).join('')}</select></label><div class="attrs">${['FUE','DES','CON','INT','SAB','CAR'].map((a,i)=>field('a'+i,a,c.abilities[i],'number')).join('')}</div><small>Modificadores de característica: suelo((valor − 10) / 2). No se aplican automáticamente a los totales declarados.</small><div class="row">${field('hp','PG actuales',c.hp,'number')}${field('maxHp','PG máximos',c.maxHp,'number')}${field('ac','CA total',c.ac,'number')}</div><div class="row">${field('speed','Velocidad en casillas',c.speed,'number')}${field('initiative','Iniciativa total',c.initiative,'number')}${field('attack','Ataque total',c.attack,'number')}</div><div class="row">${field('damage','Daño')}${field('saves','Fortaleza, Reflejos, Voluntad',c.saves.join(','))}</div>${meleeFields(c)}${skillFields(c)}${['skills','feats','equipment','load','spells','resources','conditions','notes'].map((k,i)=>`<label>${['Habilidades y origen de modificadores','Dotes y referencias','Equipo e inventario','Carga y capacidad','Conjuros y espacios','Recursos y usos restantes','Condiciones y duraciones','Notas y referencias verificadas'][i]}<textarea name="${k}">${esc(c[k]||'')}</textarea></label>`).join('')}<label class="check"><input type="checkbox" name="enemy" ${c.enemy?'checked':''}> ${c.npcCreation?'PNJ dirigido por la aventura':'Adversario controlado por el anfitrión'}</label><div class="toolbar"><button class="primary">Guardar ficha</button>${ref('reglas',1,'Consultar creación de personajes')}</div></form>`);
 $('#characterForm button.primary').disabled=!!c.npcCreation&&!snapshot.me.host;
 $('#characterForm').onsubmit=run(async e=>{let d=values(e.target);d.abilities=Array.from({length:6},(_,i)=>Number(d['a'+i]));d.saves=d.saves.split(',').map(Number);d.skillTotals=parseSkillTotals(d.skillTotalsInput);d.enemy=!!d.enemy;if(d.basicMelee)d.meleeProfile={flatAc:Number(d.flatAc),criticalMin:Number(d.criticalMin),multiplier:Number(d.multiplier)};if(cid)d.id=cid;await act('character',{character:d});$('#modal').close();toast('Ficha guardada en la campaña')})}
function manualForm(index){const pending=index===undefined?'':snapshot.state.pending[index]?.reason||'';modal(`<div class="eyebrow">REGLA NO AUTOMATIZADA</div><h2>Resolución manual asistida</h2><p class="hint">Consulta el manual, realiza las tiradas necesarias y registra el resultado confirmado. Los cambios de PG, recursos y condiciones se aplican juntos y quedan en el historial.</p><form id="manualForm"><label>Motivo<input name="reason" required value="${esc(pending)}"></label><label>Referencia · libro, apartado, página PDF<input name="reference" required placeholder="Si no se verifica: criterio provisional o regla casera"></label><label>Resultado y cálculo<textarea name="resolution" required></textarea></label><label>Personaje afectado<select name="character"><option value="">Sin modificación de ficha</option>${snapshot.state.characters.map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join('')}</select></label><label>Coste de acci&oacute;n<select name="actionCost"><option value="none">Sin coste</option><option value="standard">Est&aacute;ndar</option><option value="move">Movimiento</option><option value="full">Asalto completo</option><option value="swift">R&aacute;pida</option><option value="immediate">Inmediata</option></select></label><label>Cambio de PG · negativo = daño<input type="number" name="hpDelta" value="0"></label><label>Condiciones · dejar vacío conserva las actuales<input name="conditions"></label><label>Recursos · dejar vacío conserva los actuales<input name="resources"></label><button class="primary">Confirmar y registrar</button></form>`);$('#manualForm').onsubmit=run(async e=>{let d=values(e.target);if(!d.conditions)delete d.conditions;if(!d.resources)delete d.resources;if(index!==undefined)d.pendingIndex=index;await act('manual',d);$('#modal').close()})}
document.addEventListener('click',e=>{let target=e.target.closest('[data-tab],[data-book],[data-character],[data-pending]');if(!target)return;if(target.dataset.tab)chooseTab(target.dataset.tab);if(target.dataset.book){chooseTab('books',false);openBook(target.dataset.book,Number(target.dataset.page))}if(target.dataset.character)characterForm(target.dataset.character);if(target.dataset.pending!==undefined)manualForm(Number(target.dataset.pending))});
$('#closeModal').onclick=()=>$('#modal').close();
$('#createForm').onsubmit=run(async e=>{ensureCampaignCanChange();const r=await api('/api/create',values(e.target));token=r.token;localStorage.setItem('cronicas-token',token);await refresh(true)});
$('#joinForm').onsubmit=run(async e=>{ensureCampaignCanChange();let r=await api('/api/join',values(e.target));token=r.token;localStorage.setItem('cronicas-token',token);const address=new URL(location.href);address.searchParams.delete('invite');history.replaceState(history.state,'',address.pathname+address.search+address.hash);await refresh(true)});
$('#libraryBtn').onclick=run(()=>openCampaignLibrary());$('#manageAccesses').onclick=run(()=>openCampaignLibrary());$('#resume').onclick=run(()=>refresh(true));$('#exitBtn').onclick=run(async()=>{ensureCampaignCanChange();bookReader.reset();document.body.classList.remove('reader-wide');$('#app').hidden=true;$('#welcome').hidden=false;$('#resume').hidden=!token;$('#savedLibraryPanel').hidden=false;renderSavedCampaigns()});
$('#inviteBtn').onclick=run(async()=>{const link=location.origin+'/?invite='+encodeURIComponent(snapshot.invite);modal('<h2>Reunir al grupo</h2><p>Comparte este código con quienes tengan acceso al servidor. El nombre de jugador no sustituye la credencial de reconexión guardada en su navegador.</p><label>Código<input readonly value="'+esc(snapshot.invite)+'"></label><label>Enlace<input readonly value="'+esc(link)+'"></label><p class="hint">127.0.0.1 solo abre en este ordenador. Para red local inicia con HOST=0.0.0.0 y usa la dirección del servidor. Para Internet se requiere alojamiento, HTTPS y configuración de acceso.</p>')});
$('#addCharacter').onclick=()=>characterForm();$('#manualBtn').onclick=()=>manualForm();
$('#composer').onsubmit=run(async()=>{const reason=conversationUnavailable();if(reason)throw Error(reason);let text=$('#message').value;await act('talk',{text,character:$('#speaker').value||null,kind:$('#messageKind').value,director:$('#useAI').checked&&$('#messageKind').value!=='private'});$('#message').value='';$('#story').scrollTop=$('#story').scrollHeight});
$('#message').onkeydown=e=>{if(e.ctrlKey&&e.key==='Enter')$('#composer').requestSubmit()};
$('#speaker').addEventListener('change',renderComposerAvailability);
$('#messageKind').onchange=()=>{if($('#messageKind').value==='private')$('#useAI').checked=false;renderSpeakerChoices()};
$('#journalForm').onsubmit=run(async e=>{const d=values(e.target);for(const key of ['objectives','allies','enemies','unknowns'])d[key]=d[key].split('\n').filter(Boolean);await act('journal',d);toast('Diario guardado')});
$('#nextScene').onclick=run(async()=>{let location=prompt('Lugar de la siguiente escena',snapshot.state.location);if(location!==null)await act('scene',{location})});
$('#rollForm').onsubmit=run(async e=>{const d=physical(values(e.target));await act('roll',d);chooseTab('story')});
$('#oracleForm').onsubmit=run(async e=>{const d=physical(values(e.target));d.uncertain=!!d.uncertain;await act('oracle',d);chooseTab('journal')});
const npcButton=document.createElement('button');npcButton.type='button';npcButton.textContent='Generar PNJ';$('#voluntary').before(npcButton);npcButton.onclick=()=>{modal(`<h2>Una nueva cara en el camino</h2><form id="npcForm"><label>Nombre<input name="name" required></label><label>Probabilidad de buen trato<select name="probability"><option value="neutral">Neutral</option><option>probable</option><option>muy probable</option><option>improbable</option><option>muy improbable</option></select></label><label>Dados fisicos d10,d8,d6 (opcional)<input name="physical"></label><label>Dado fisico mas alejado<select name="farthest"><option value="">Sin determinar</option><option>d10</option><option>d8</option><option>d6</option></select></label><p class="hint">TREY PDF pp.26-27. La capacidad depende de la posicion fisica; no se deduce del valor del dado. El comportamiento no sustituye Diplomacia.</p><button class="primary">Registrar PNJ</button></form>`);$('#npcForm').onsubmit=run(async e=>{const d=physical(values(e.target));if(!d.farthest)delete d.farthest;await act('npc',d);$('#modal').close();chooseTab('journal')})};
$('#voluntary').onclick=run(async()=>{if(!confirm('Evento voluntario normal: ganas FH iguales al número de escena antes del punto de giro. Solo uno por escena. ¿Confirmar?'))return;await act('voluntary');chooseTab('journal')});
$('#spend').onclick=()=>{modal(`<h2>Un giro a vuestro favor</h2><form id="spendForm"><label>Beneficio<select name="benefit">${Object.entries({'repetir habilidad':2,'éxito habilidad':4,'acción adicional':2,'éxito combate':4,'evitar muerte':6,'invertir oráculo':6,'reducir excepcional':4,'grado detalle':4,'evento positivo':6,'reducir evento':4,'grado comportamiento':2,'grado capacidad':4,'objeto útil':2,'ayuda':6}).map(([k,v])=>`<option value="${k}">${k} · ${v} FH</option>`).join('')}</select></label><label>Interpretación y alcance<input name="interpretation" required></label><label class="check"><input type="checkbox" name="consent" required> Todo el grupo ha dado su consentimiento.</label><p class="hint">Se descuentan FH y se abre una resolución asistida. Las ventajas de TREY sobre Pathfinder son una adaptación declarada.</p><button class="primary">Registrar gasto</button></form>`);$('#spendForm').onsubmit=run(async e=>{let d=values(e.target);d.consent=!!d.consent;await act('spend',d);$('#modal').close();chooseTab('journal')})};
$('#startCombat').onclick=run(()=>act('combat',{automateEnemies:$('#autoEnemies').checked}));$('#nextTurn').onclick=run(()=>act('turn'));$('#endCombat').onclick=run(()=>act('endcombat'));$('#expandBoard').onclick=()=>document.body.classList.toggle('expanded');$('#boardCharacter').onchange=()=>{path=[];renderBoard()};
$('#grid').onclick=run(async e=>{const cell=e.target.closest('[data-x]');if(!cell)return;const x=+cell.dataset.x,y=+cell.dataset.y,tool=$('#tool').value;if(tool==='pan')return;if(tool==='measure'){ruler=ruler.length===1?[ruler[0],[x,y]]:[[x,y]];renderBoard();return}if(tool!=='move'){await act('terrain',{x,y,terrain:tool});return}const clicked=boardCharacters(snapshot.state).find(c=>c.x===x&&c.y===y);if(clicked){if(snapshot.me.host||clicked.owner===snapshot.me.id){if($('#boardCharacter').value!==clicked.id||path.length){$('#boardCharacter').value=clicked.id;path=[];renderBoard()}}else{$('#attackTarget').value=clicked.id;renderAttack();toast('Objetivo seleccionado: '+clicked.name)}return}const ch=snapshot.state.characters.find(c=>c.id===$('#boardCharacter').value);if(!ch)throw Error('Crea y selecciona una ficha');let prev=path.length?path[path.length-1]:[ch.x,ch.y];if(Math.max(Math.abs(prev[0]-x),Math.abs(prev[1]-y))!==1)throw Error('Selecciona una casilla adyacente al último punto');path.push([x,y]);renderBoard()});
$('#clearPath').onclick=()=>{path=[];renderBoard()};$('#confirmMove').onclick=run(async()=>{if(!path.length)throw Error('Traza un recorrido primero');if(!confirm($('#pathInfo').textContent+'\n¿Has revisado las consecuencias conocidas y las reglas pendientes con la mesa?'))return;await act('move',{character:$('#boardCharacter').value,path,acknowledge:true})});
$('#openPage').onclick=()=>openBook();$('#book').onchange=()=>openBook($('#book').value,1);$('#bookmark').onclick=run(async()=>{const label=prompt('Nombre del marcador',names[$('#book').value]+' · p.'+$('#page').value);if(label)await act('bookmark',{book:$('#book').value,page:+$('#page').value,label})});
async function find(q){const data=await api('/api/search?q='+encodeURIComponent(q)+'&book='+$('#book').value);$('#searchResults').innerHTML=data.map(r=>`<div class="result">${ref(r.book,r.page)}<p>${esc(r.text)}</p></div>`).join('')||'<p>No hay coincidencias fiables en el texto extraído. Consulta el original; puede requerir OCR.</p>'}
$('#searchForm').onsubmit=run(()=>find($('#searchQuery').value));$('#indexBtn').onclick=run(()=>find('índice contenido'));$('#askRule').onclick=run(async()=>{$('#ruleAnswer').textContent='Consultando fuentes y servicio de IA…';try{let r=await api('/api/rules',{q:$('#searchQuery').value});$('#ruleAnswer').innerHTML='<p>'+esc(r.answer)+'</p>'+r.refs.map(v=>ref(v.book,v.page)).join('')}catch(e){$('#ruleAnswer').textContent=e.message}});
$('#exportBtn').onclick=run(async()=>{const data=await api('/api/export',{});let url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));let a=document.createElement('a');a.href=url;a.download='cronica-'+snapshot.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
$('#importFile').onchange=run(async e=>{const file=e.target.files[0];if(!file)return;if(!confirm('La copia sustituirá el estado de esta sala. Los personajes se asignarán al anfitrión que importa. Exporta antes si deseas conservar el estado actual.'))return;await act('import',{campaign:JSON.parse(await file.text())});toast('Copia recuperada')});
async function loadSystemChoices(){
 const {systems}=await api('/api/systems');if(systems.length<2)return;
 const form=$('#createForm'),label=document.createElement('label');label.id='systemPicker';
 label.innerHTML='Reglamento<select name="ruleset">'+systems.map(s=>`<option value="${esc(s.id)}">${esc(s.name)}</option>`).join('')+'</select><small id="systemChoiceHint"></small>';
 form.querySelector('label').before(label);
 const notes=form.querySelector(':scope > small'),original=notes.textContent;
 label.querySelector('select').onchange=()=>{
  const selected=systems.find(s=>s.id===label.querySelector('select').value),pf=selected.id==='pathfinder-1e';
  form.elements.threshold.closest('label').hidden=!pf;form.elements.difficulty.closest('label').hidden=!pf;
  notes.textContent=pf?original:'La cobertura depende del reglamento seleccionado. Los paquetes importados no certifican correspondencia con el manual.';
  $('#systemChoiceHint').textContent=selected.status==='experimental'?'Experimental: recorrido en pruebas, con límites indicados al entrar.':(selected.coverage||[]).join(' · ');
 };label.querySelector('select').onchange();
}
async function init(){renderSavedCampaigns();try{model=await api('/api/status');await loadSystemChoices();$('#capabilities').innerHTML=`<p><strong>● Guardado persistente</strong><br>${esc(model.storage)}</p><p>${model.aiConfigured?'● IA configurada: '+esc(model.model):'○ Director de IA sin configurar'}<br>Conexión real a Claude Haiku; sin respuestas prefijadas.</p><p>${Object.entries(model.books).map(([k,n])=>esc(names[k])+': '+n+' páginas indexadas').join('<br>')}</p>`;$('#aiHint').textContent=model.aiConfigured?'El director responderá si activas «Responder con IA». Las tiradas y herramientas funcionan sin IA.':'El director no está disponible en esta mesa. Puedes usar las fichas, los dados y el tablero sin IA.';$('#useAI').disabled=!model.aiConfigured;if(!model.aiConfigured)$('#useAI').checked=false;$('#resume').hidden=!token;const invite=new URLSearchParams(location.search).get('invite');if(invite){$('#inviteInput').value=invite;$('#joinPanel').open=true;}if(token&&!invite){const pending=JSON.parse(localStorage.getItem('cronicas-pending')||'null');if(pending&&pending.token===token){try{busy=true;await recoverSubmission(pending);localStorage.removeItem('cronicas-pending');toast('Envío recuperado')}catch(e){if(e.confirmed)localStorage.removeItem('cronicas-pending');toast(e.message)}finally{busy=false}}await refresh(true)}}catch(e){toast(e.message)}}
const tabletopControls=window.TabletopControls.mount({
 scroller:$('.board-scroll'),grid:$('#grid'),tool:$('#tool'),zoom:$('#zoom'),snapshot:()=>snapshot&&(!snapshot.state.ruleset||snapshot.state.ruleset==='pathfinder-1e')?{...snapshot,state:{...snapshot.state,characters:boardCharacters(snapshot.state)}}:null,
 select:id=>{$('#boardCharacter').value=id;path=[];renderBoard()},
 preview:points=>{path=points;renderBoard()},measure:points=>{ruler=points;renderBoard()},
 cancel:()=>{path=[];ruler=[];if(snapshot&&(!snapshot.state.ruleset||snapshot.state.ruleset==='pathfinder-1e'))renderBoard()},openSheet:characterForm,tab:chooseTab,
 focusChat:()=>$('#message').focus(),notify:toast,repaint:()=>{if(snapshot&&(!snapshot.state.ruleset||snapshot.state.ruleset==='pathfinder-1e'))renderBoard()}
});
let readerExpanded=false;
const bookReader=window.BookReader.mount({token:()=>token,image:$('#bookPageImage'),status:$('#bookLoadStatus'),input:$('#page'),total:$('#bookPageTotal'),previous:$('#previousBookPage'),next:$('#nextBookPage')});
$('#previousBookPage').onclick=()=>openBook($('#book').value,Number($('#page').value)-1);
$('#nextBookPage').onclick=()=>openBook($('#book').value,Number($('#page').value)+1);
$('#readerZoomOut').onclick=()=>bookReader.zoom(-25);
$('#readerZoomIn').onclick=()=>bookReader.zoom(25);
$('#readerFit').onclick=()=>bookReader.fit();
$('#expandReader').onclick=()=>{readerExpanded=!readerExpanded;document.body.classList.toggle('reader-wide',readerExpanded);$('#expandReader').textContent=readerExpanded?'Volver a la mesa':'Ampliar lectura'};
let syncing=false;
async function syncVisible(){
 if(!token||document.hidden||$('#app').hidden||busy||syncing)return;
 syncing=true;
 try{await refresh()}catch{$('#sync').textContent='Sin conexi\u00f3n - reintentando'}finally{syncing=false}
}
setInterval(syncVisible,15000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)syncVisible()});
init();
