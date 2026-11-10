const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
let token=localStorage.getItem('cronicas-token'), model={}, snapshot, snapshotToken, path=[], ruler=[], lastVersion=-1, busy=false, toastTimer, gridFocus=[0,0], gridFocusKey;
let submittedMovementPreview,messageRevision=0,submittedMessage;
const names={reglas:'Reglas básicas',bestiario:'Bestiario',trey:'TREY'};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const characterIsConscious=c=>!!c&&(c.hp>=0||(c.hp>-c.abilities[2]&&c.stable===true&&c.recoveryState?.conscious===true));
const characterHealthLabel=c=>c.hp<=-c.abilities[2]?'Ha muerto':c.hp>0?'':characterIsConscious(c)?'Incapacitado':c.stable===true?'Inconsciente y estable':'Moribundo';
const characterMovementCells=c=>c&&characterIsConscious(c)&&Number.isInteger(c.speed)?Math.floor(c.speed/(c.hp<=0?2:1)):0;
const boardCharacters=s=>s.boardScenes?s.characters.filter(c=>c.sceneId===s.boardScenes.current):s.characters;
function toast(s){$('#toast').textContent=s;$('#toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').hidden=true,7000)}
async function api(url,body,access=token){
 let response;
 try{response=await fetch(url,{method:body?'POST':'GET',headers:{'Content-Type':'application/json',Authorization:'Bearer '+access},body:body?JSON.stringify(body):undefined})}
 catch{throw Error('No se pudo conectar con la mesa. Vuelve a intentarlo cuando tengas conexión.')}
 let data;
 try{data=await response.json()}
 catch{throw Error('La mesa no devolvió una respuesta válida. Vuelve a intentarlo.')}
 if(!response.ok){const error=Error(data?.error||'Error del servidor');error.confirmed=response.status>=400&&response.status<500;error.status=response.status;throw error}
 return data;
}
function values(form){return Object.fromEntries(new FormData(form))}
function prepareEntryInvitation(invite){
 document.body.classList.toggle('joining-campaign',!!invite);$('#createForm').hidden=!!invite;
 $('#welcome>h1').textContent=invite?'Entra en la aventura':'Tu próxima aventura';
 $('#welcome>.intro').textContent=invite?'Tu grupo ya tiene una partida preparada. Entra con tu nombre.':'Continúa una partida o empieza con tu personaje.';
 $('#inviteInput').value=invite||'';$('#joinPanel').open=!!invite;
}
function physical(d){if(d.physical?.trim())d.physical=d.physical.split(',').map(Number);else delete d.physical;return d}
async function recoverSubmission(saved){
 saved=await withSubmissionLock(cell=>{
  const outcome=cell.outcome(saved);
  if(outcome==='accepted')return {...saved,confirmed:true};
  if(outcome==='discarded'){const error=Error('Este envío ya se descartó. No se ha repetido; revisa la partida antes de elegir otra acción.');error.confirmed=true;throw error;}
  if(!sameSubmission(cell.value,saved))throw Error('El envío pendiente cambió en otra pestaña. Revisa el aviso antes de recuperarlo.');
  return cell.value;
 },[saved]);
 if(saved.confirmed===true)return saved;
 try{await api('/api/action',saved.body)}catch(error){
  if(error.status!==409||saved.body.type!=='resolve_pack_request')throw error;
  await refresh(true);
  if(token!==saved.token)throw error;
  const pending=snapshot?.state.narrativeView?.pending;
  if(pending?.id!==saved.body.request||pending.randomnessScope!=='pending-resolution-v2')throw error;
  const body={...saved.body,id:crypto.randomUUID(),version:snapshot.version};
  const replacement={token:saved.token,body};
  if(!await replaceSubmission(saved,replacement))throw Error('El envío pendiente cambió en otra pestaña. Revisa su recuperación antes de continuar.');
  saved=replacement;
  await api('/api/action',body);
 }
 return acknowledgeSubmission(saved);
}
let submissionDatabase;
function openSubmissionDatabase(){
 if(!submissionDatabase)submissionDatabase=new Promise((resolve,reject)=>{
  const request=indexedDB.open('cronicas-pending-v1',1);let failed=false;
  request.onupgradeneeded=()=>request.result.createObjectStore('outbox');
  request.onerror=()=>{failed=true;reject(request.error)};
  request.onblocked=()=>{failed=true;reject(Error('Otra pestaña está actualizando los envíos. Ciérrala y vuelve a intentarlo.'))};
  request.onsuccess=()=>{const db=request.result;if(failed){db.close();return}db.onversionchange=()=>{db.close();submissionDatabase=undefined};resolve(db)};
 }).catch(error=>{submissionDatabase=undefined;throw error});
 return submissionDatabase;
}
function submissionIdentity(receipt){return JSON.stringify([receipt.token,receipt.body.id])}
function submissionBodyIdentity(receipt){
 const ordered=value=>Array.isArray(value)?value.map(ordered):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,ordered(value[key])])):value;
 return JSON.stringify([receipt.token,ordered(receipt.body)]);
}
function sameSubmission(left,right){return !!left&&!!right&&submissionBodyIdentity(left)===submissionBodyIdentity(right)}
async function submissionEntry(receipt){
 const copy=JSON.parse(JSON.stringify(receipt));
 if(typeof copy.token!=='string'||!copy.body||typeof copy.body.id!=='string')throw Error('No se puede leer el envío guardado. Conserva los datos del navegador y vuelve a abrir la partida.');
 const hashes=await Promise.all([submissionIdentity(copy),submissionBodyIdentity(copy)].map(identity=>crypto.subtle.digest('SHA-256',new TextEncoder().encode(identity))));
 const hex=hash=>Array.from(new Uint8Array(hash),byte=>byte.toString(16).padStart(2,'0')).join('');
 return {key:hex(hashes[0]),bodyKey:hex(hashes[1]),receipt:copy};
}
async function submissionTransaction(change,candidates=[],depth=0){
 const mirrorText=localStorage.getItem('cronicas-pending'),mirror=mirrorText?JSON.parse(mirrorText):null;
 const entries=await Promise.all([mirror,...candidates].filter(Boolean).map(submissionEntry));
 const mirrorEntry=mirror?entries[0]:null,known=new Map(entries.map(entry=>[submissionIdentity(entry.receipt),entry]));
 const db=await openSubmissionDatabase();
 return new Promise((resolve,reject)=>{
  const transaction=db.transaction('outbox','readwrite',{durability:'strict'}),store=transaction.objectStore('outbox'),request=store.get('state');
  let record,result,operationError,storageError;
  request.onsuccess=()=>{
   try{
    const previous=JSON.stringify(request.result||null);
    record=request.result||{format:'cronicas-pending-outbox-3',queue:[],completed:[]};
    if(record.format==='cronicas-pending-outbox-1'&&Array.isArray(record.completed))record={...record,format:'cronicas-pending-outbox-3',completed:record.completed.map(key=>({key,kind:'legacy-id',status:'unknown'}))};
    if(record.format==='cronicas-pending-outbox-2'&&Array.isArray(record.completed))record={...record,format:'cronicas-pending-outbox-3',completed:record.completed.map(entry=>({key:entry.key,kind:'legacy-id',status:'unknown'}))};
    if(record.format!=='cronicas-pending-outbox-3'||!Array.isArray(record.queue)||!Array.isArray(record.completed))throw Error('No se puede leer la recuperación local de envíos. Conserva los datos del navegador.');
    if(record.queue.some(entry=>!entry||!/^[a-f0-9]{64}$/.test(entry.key)||typeof entry.receipt?.token!=='string'||typeof entry.receipt?.body?.id!=='string'||(entry.bodyKey!==undefined&&!/^[a-f0-9]{64}$/.test(entry.bodyKey)))||record.completed.some(entry=>!entry||!/^[a-f0-9]{64}$/.test(entry.key)||!['accepted','discarded','unknown'].includes(entry.status)||!['body','legacy-id'].includes(entry.kind)))throw Error('No se puede leer la recuperación local de envíos. Conserva los datos del navegador.');
    record.completed=record.completed.slice(-128);
    const mirrorOutcome=mirrorEntry&&record.completed.find(entry=>entry.kind==='body'&&entry.key===mirrorEntry.bodyKey)?.status;
    if(mirrorEntry&&(!mirrorOutcome||mirrorOutcome==='unknown')){
     const existing=record.queue.find(entry=>entry.key===mirrorEntry.key);
     if(!existing)record.queue.push(mirrorEntry);
     else if(mirrorEntry.receipt.confirmed===true&&sameSubmission(existing.receipt,mirrorEntry.receipt))existing.receipt.confirmed=true;
    }
    for(const entry of record.queue){const prepared=known.get(submissionIdentity(entry.receipt));if(prepared&&sameSubmission(entry.receipt,prepared.receipt)){if(entry.bodyKey&&entry.bodyKey!==prepared.bodyKey)throw Error('La recuperación local no coincide con el envío guardado. Conserva los datos del navegador.');entry.bodyKey=prepared.bodyKey}}
    const originalQueue=record.queue.slice(),originalCompleted=record.completed.slice(),head=record.queue[0];
    const lookup=receipt=>known.get(submissionIdentity(receipt))||record.queue.find(entry=>submissionIdentity(entry.receipt)===submissionIdentity(receipt));
    const cell={value:head?.receipt||null,outcome:receipt=>record.completed.find(entry=>entry.kind==='body'&&entry.key===lookup(receipt)?.bodyKey)?.status};
    try{
     result=change(cell);
     if(result&&typeof result.then==='function')throw Error('La actualización local del envío debe terminar antes de continuar.');
     if(cell.value!==head?.receipt&&!(cell.value===null&&!head)){
      const next=cell.value?lookup(cell.value):null;
      if(cell.value&&!next)throw Error('El envío cambió antes de guardarse. Vuelve a intentarlo.');
      if(head&&next?.key===head.key&&!sameSubmission(head.receipt,cell.value))throw Error('El contenido del envío cambió. Se conserva el original; revisa el aviso de recuperación.');
      if(head){record.queue.shift();if(!next||next.key!==head.key){const key=head.bodyKey||head.key,kind=head.bodyKey?'body':'legacy-id';record.completed=record.completed.filter(entry=>entry.key!==key||entry.kind!==kind);record.completed.push({key,kind,status:head.bodyKey?(head.receipt.confirmed===true?'accepted':'discarded'):'unknown'})}}
      if(next){record.queue=record.queue.filter(entry=>entry.key!==next.key);record.queue.unshift({key:next.key,bodyKey:next.bodyKey,receipt:JSON.parse(JSON.stringify(cell.value))});record.completed=record.completed.filter(entry=>entry.kind!=='body'||entry.key!==next.bodyKey)}
      record.completed=record.completed.slice(-128);
     }
    }catch(error){operationError=error;record.queue=originalQueue;record.completed=originalCompleted}
    if(JSON.stringify(record)!==previous)store.put(record,'state');
   }catch(error){storageError=error;transaction.abort()}
  };
  transaction.onabort=()=>reject(storageError||transaction.error||Error('No se pudo guardar el envío en este navegador. No se ha enviado al servidor.'));
  transaction.oncomplete=async()=>{
   try{
    const next=record.queue[0]?.receipt,value=next?JSON.stringify(next):null,current=localStorage.getItem('cronicas-pending');
    if(current&&current!==mirrorText&&current!==value){
     if(depth>=4)throw Error('Otra pestaña sigue cambiando el envío. Espera un momento y vuelve a recuperarlo.');
     await submissionTransaction(()=>{},[],depth+1);
    }else if(current!==value){
     if(value===null)localStorage.removeItem('cronicas-pending');else localStorage.setItem('cronicas-pending',value);
     if(snapshot&&!busy){renderSyncStatus();renderComposerAvailability();renderPlayGuidance(snapshot.state)}
    }
    if(operationError)reject(operationError);else resolve(result);
   }catch(error){error.persistedSubmission=record.queue[0]?.receipt.body.id;reject(error)}
  };
 });
}
async function withSubmissionLock(change,candidates=[]){
 try{
  if(!globalThis.indexedDB||!globalThis.crypto?.subtle)throw new DOMException('Local recovery unavailable','NotSupportedError');
  const update=()=>submissionTransaction(change,candidates);
  return await (navigator.locks?navigator.locks.request('cronicas-pending',update):update());
 }catch(error){
  const messages={QuotaExceededError:'No hay espacio para guardar la recuperación del envío. Conserva tus datos y vuelve a intentarlo cuando haya espacio disponible.',SecurityError:'El navegador no permite guardar la recuperación del envío. Permite el almacenamiento de datos de esta aplicación y vuelve a intentarlo.',NotSupportedError:'Este navegador no permite guardar la recuperación del envío. Abre la partida con un navegador compatible.',UnknownError:'No se pudo actualizar la recuperación local. Conserva los datos del navegador y vuelve a abrir la partida.',AbortError:'No se pudo actualizar la recuperación local. Conserva los datos del navegador y vuelve a abrir la partida.',InvalidStateError:'No se pudo actualizar la recuperación local. Conserva los datos del navegador y vuelve a abrir la partida.'};
  if(messages[error.name]){const explained=Error(messages[error.name]);explained.name=error.name;if(error.persistedSubmission)explained.persistedSubmission=error.persistedSubmission;throw explained}
  throw error;
 }
}
async function replaceSubmission(saved,next){
 return withSubmissionLock(cell=>{
  const current=cell.value;
  if(!sameSubmission(current,saved))return false;
  cell.value=next;return true;
 },[saved,next]);
}
async function clearSubmission(saved){
 return withSubmissionLock(cell=>{
  const current=cell.value;
  if(!sameSubmission(current,saved))return false;
  cell.value=null;return true;
 },[saved]);
}
function clearSubmittedMovementPreview(saved){
 const previous=submittedMovementPreview;
 if(previous?.id!==saved.body.id)return;
 submittedMovementPreview=undefined;
 if(path!==previous.path||$('#boardCharacter').value!==saved.body.character||JSON.stringify(path)!==JSON.stringify(saved.body.path))return;
 path=[];renderBoard();
}
async function acknowledgeSubmission(saved){
 const accepted={...saved,confirmed:true};
 await withSubmissionLock(cell=>{
  const current=cell.value;
  if(sameSubmission(current,saved))cell.value=accepted;
 },[accepted]);
 return accepted;
}
function ensureSubmissionCanStart(){
 if(busy)throw Error('Hay una acción en curso');
 const saved=JSON.parse(localStorage.getItem('cronicas-pending')||'null');
 if(saved){renderSubmissionFeedback();throw Error(saved.token===token?'Recupera el envío pendiente antes de realizar otra acción.':'Hay un envío pendiente en otra partida. Ábrela para recuperarlo antes de enviar otra acción.')}
}
async function reserveSubmission(saved){
 const reserve=cell=>{
  if(cell.value)throw Error('Hay un envío pendiente. Recupéralo antes de enviar otra acción.');
  cell.value=saved;
 };
 await withSubmissionLock(reserve,[saved]);
}
async function act(type,data={}){
 ensureSubmissionCanStart();
 const body=JSON.parse(JSON.stringify({...data,type,id:crypto.randomUUID(),version:snapshot.version})),draftRevision=messageRevision;
 busy=true;renderComposerAvailability();$('#sync').textContent='Resolviendo…';
 const movement=['move','five_foot_step'].includes(type),preparedPath=path;
 if((!snapshot.state.ruleset||snapshot.state.ruleset==='pathfinder-1e')&&['talk','start_adventure','continue_adventure','next_adventure'].includes(type))body.captureContract=type==='start_adventure'&&body.openingContract==='authored-opening-1'?'pf-authored-opening-1':'pf-director-action-1';
 let saved={token,body},stored=false,accepted=false;
 try{
  await reserveSubmission(saved);stored=true;
  if(type==='talk')submittedMessage={token:saved.token,id:body.id,revision:draftRevision};
  if(movement)submittedMovementPreview={id:body.id,path:preparedPath};
  await api('/api/action',body);accepted=true;saved=await acknowledgeSubmission(saved);if(movement)clearSubmittedMovementPreview(saved);else path=[];
  await refresh(true);await clearSubmission(saved);
 }catch(e){
  if(!stored&&type==='talk'&&e.persistedSubmission===body.id)submittedMessage={token:saved.token,id:body.id,revision:draftRevision};
  if(!stored&&e.name==='QuotaExceededError')throw Error('No hay espacio en el navegador para conservar este envío. No se ha enviado al servidor; conserva tus accesos y vuelve a intentarlo cuando haya espacio disponible.');
  if(!accepted&&e.confirmed)await clearSubmission(saved);
  if(stored&&!accepted){try{await refresh(true)}catch{}}
  throw e;
 }finally{busy=false;renderComposerAvailability();renderSubmissionFeedback()}
}
function run(fn){return async e=>{e?.preventDefault();try{await fn(e)}catch(err){toast(err.message)}}}
function renderSyncStatus(waiting=!!JSON.parse(localStorage.getItem('cronicas-pending')||'null')){
 const saved=JSON.parse(localStorage.getItem('cronicas-pending')||'null');
 $('#sync').textContent=waiting?(saved?.token!==token?'Otra partida pendiente':saved?.confirmed===true?'Resultado pendiente':'Envío pendiente'):'● Guardado en Firebase';$('#sync').classList.toggle('pending',waiting);
}
async function refresh(force=false){
 if(!token)return;
 const requestedToken=token,previous=snapshot,params=new URLSearchParams(),receipt=JSON.parse(localStorage.getItem('cronicas-pending')||'null');
 if(!force&&previous&&snapshotToken===requestedToken)params.set('version',previous.version);
 const cached=previous?.me.host&&snapshotToken===requestedToken&&previous.state.authoringWorkspace&&previous.state.authoringWorkspaceRef?.sha256;
 if(cached)params.set('workspace',cached);
 const next=await api('/api/state'+(params.size?'?'+params:''));
 if(token!==requestedToken)return;
 if(next.unchanged){
  if(receipt?.token===requestedToken&&receipt.confirmed===true){await clearSubmission(receipt);if(token!==requestedToken)return;renderComposerAvailability();renderSubmissionFeedback()}
  renderSyncStatus();return;
 }
 if(next.workspaceUnchanged){
  if(!cached||next.workspaceUnchanged!==cached||next.id!==previous.id||next.me.id!==previous.me.id||!next.me.host)throw Error('La caché privada no corresponde a este acceso; recarga para recuperarla.');
  next.state.authoringWorkspace=previous.state.authoringWorkspace;
 }
 const completed=receipt?.token===requestedToken&&receipt.confirmed===true&&await clearSubmission(receipt);
 if(token!==requestedToken)return;
 if(previous?.state.boardScenes?.current!==next.state.boardScenes?.current){path=[];ruler=[];}
 snapshot=next;snapshotToken=requestedToken;rememberCampaign();renderSyncStatus();
 if(!force&&!completed&&lastVersion===next.version)return;lastVersion=next.version;render();
}
function chooseTab(id,loadDocument=true){if(id==='board'&&window.matchMedia('(min-width:1100px)').matches)id='story';if(id==='books'&&window.matchMedia('(max-width:1099px)').matches)readerExpanded=true;document.body.classList.toggle('board-tab-active',id==='board');$$('.tab').forEach(x=>x.classList.toggle('active',x.id===id));$$('[data-tab]').forEach(x=>x.classList.toggle('active',x.dataset.tab===id));renderReaderMode();if(id==='books'&&loadDocument)openBook();}
function renderReaderMode(){
 const expanded=readerExpanded&&$('#books').classList.contains('active');
 document.body.classList.toggle('reader-wide',expanded);$('#expandReader').textContent=expanded?'Cerrar vista ampliada':'Ampliar lectura';$('#expandReader').setAttribute('aria-pressed',String(expanded));
}
function ref(book,page,label){return `<button type="button" class="rule-link" data-book="${esc(book)}" data-page="${Number(page)}">${esc(label||names[book]+' · PDF p.'+page)} ↗</button>`}
async function showActionResult(type,data,show){
 const access=token,tab=$('[data-tab].active')?.dataset.tab,focus=document.activeElement;
 const unchanged=()=>token===access&&$('[data-tab].active')?.dataset.tab===tab&&!$('#modal').open&&(document.activeElement===focus||document.activeElement===document.body);
 try{await act(type,data)}catch(error){if(unchanged()&&JSON.parse(localStorage.getItem('cronicas-pending')||'null')?.token===access)$('#playGuidanceAction').focus();throw error}
 if(unchanged())show?.();
}
function showInvestigationScene(focusChoice=false){
 chooseTab('story');
 const heading=$('#investigationPanel > h3');if(!heading)return;
 const guide=$('#playGuidance'),area=$('#story'),offset=!guide.hidden&&guide.parentElement===area?guide.getBoundingClientRect().height+(parseFloat(getComputedStyle(area).paddingTop)||0):0;
 heading.tabIndex=-1;heading.style.scrollMarginTop=(offset+12)+'px';heading.scrollIntoView({block:'start'});
 (focusChoice?$('#investigationForm [name=opportunity]')||heading:heading).focus({preventScroll:true});
}
function showAdventureIntroduction(focus=true){
 if(focus)chooseTab('story');
 const scene=$$('#messages .message').findLast(message=>message.matches('.scene,.director'));if(!scene)return;
 const target=scene.querySelector('.speaker')||scene,area=$('#story'),guide=$('#playGuidance');
 const offset=!guide.hidden&&guide.parentElement===area?guide.getBoundingClientRect().height+(parseFloat(getComputedStyle(area).paddingTop)||0):0;
 target.style.scrollMarginTop=(offset+12)+'px';target.scrollIntoView({block:'start'});
 if(focus){target.tabIndex=-1;target.focus({preventScroll:true})}
}
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
 const reason=conversationUnavailable(),saved=JSON.parse(localStorage.getItem('cronicas-pending')||'null'),pending=!!saved;document.body.classList.toggle('submission-pending',pending);$('#send').disabled=busy||pending||!!reason;
 $('#message').setAttribute('aria-describedby','aiHint');
 $('#aiHint').textContent=busy?'Resolviendo tu envío…':pending?(saved.token===token?'Recupera el envío pendiente antes de enviar otra acción. Puedes seguir escribiendo tu borrador.':'Hay un envío pendiente en otra partida. Ábrela para recuperarlo. Tu borrador permanece aquí.'):reason||(model.aiConfigured?'El director responderá si activas «Responder con IA». Las tiradas y herramientas funcionan sin IA.':'El director no está disponible en esta mesa. Puedes usar las fichas, los dados y el tablero sin IA.');
}
function renderSubmissionFeedback(){
 if(!snapshot||(snapshot.state.ruleset&&snapshot.state.ruleset!=='pathfinder-1e'))return;
 const saved=JSON.parse(localStorage.getItem('cronicas-pending')||'null'),pending=!!saved,hadModal=$('#modal').open;
 if(pending){renderSyncStatus(true);if(hadModal)$('#modal').close();readerExpanded=false;renderReaderMode()}
 renderPlayGuidance(snapshot.state);
 if(pending&&(hadModal||document.activeElement===document.body||['send','confirmMove','confirmStep','attackButton'].includes(document.activeElement.id)))$('#playGuidanceAction').focus();
}
async function recoverPendingSubmission(){
 if(busy)throw Error('Hay una acción en curso');
 const saved=JSON.parse(localStorage.getItem('cronicas-pending')||'null');
 if(!saved||saved.token!==token)throw Error('No hay un envío pendiente de esta partida');
 const access=token,tab=$('[data-tab].active')?.dataset.tab,focus=document.activeElement;
 const unchanged=()=>token===access&&$('[data-tab].active')?.dataset.tab===tab&&!$('#modal').open&&(document.activeElement===focus||document.activeElement===document.body);
 busy=true;$('#send').disabled=true;$('#playGuidanceAction').disabled=true;$('#sync').textContent='Recuperando envío…';
 let accepted,reading=false;
 try{
  accepted=await recoverSubmission(saved);clearSubmittedMovementPreview(accepted);reading=true;await refresh(true);await clearSubmission(accepted);
  const revision=submittedMessage?.token===saved.token&&submittedMessage.id===saved.body.id?submittedMessage.revision:0;
  if(saved.body.type==='talk'&&revision===messageRevision&&$('#message').value===saved.body.text)$('#message').value='';
  if(submittedMessage?.id===saved.body.id)submittedMessage=undefined;
  if(unchanged()){
   if(saved.body.type==='check')chooseTab('story');
   if(saved.body.type==='attack')showAttackResult(saved.body);
   if(saved.body.type==='investigate'&&snapshot.state.adventureRouteView?.completed)showRouteCompletion();
   else if(['travel_scene','continue_pf_encounter','investigate'].includes(saved.body.type))showInvestigationScene();
  }
  toast('Envío recuperado');
 }
 catch(error){if(!reading&&error.confirmed)await clearSubmission(saved);if(!reading){try{await refresh(true)}catch{}}throw error}
 finally{busy=false;renderComposerAvailability();$('#playGuidanceAction').disabled=false;renderSubmissionFeedback()}
}
function renderPlayGuidance(s){
 const panel=$('#playGuidance'),text=$('#playGuidanceText'),button=$('#playGuidanceAction');
 const checks=s.pending.filter(p=>p.check),mine=checks.filter(p=>s.characters.some(c=>c.id===p.check.character&&c.owner===snapshot.me.id)),own=mine.filter(p=>!pendingCheckUnavailable(p,s.characters.find(c=>c.id===p.check.character)));
 let message='',label='',open;
 const saved=JSON.parse(localStorage.getItem('cronicas-pending')||'null');
 if(saved){if(panel.parentElement!==$('#composer'))$('#composer').prepend(panel)}else if(panel.parentElement!==$('#story'))$('#adventureEntry').before(panel);
 if(saved&&saved.token!==token){
  message='Hay un envío pendiente en otra partida. Ábrela para recuperarlo antes de enviar otra acción.';
  label='Abrir partida pendiente';open=run(openPendingCampaign);
 }else if(saved?.token===token){
  message=saved.confirmed===true?'Tu acción está guardada. Falta cargar el resultado.':'Tu último envío aún no está confirmado. Recupéralo antes de continuar.';
  label=saved.confirmed===true?'Recuperar resultado':'Recuperar envío';open=run(recoverPendingSubmission);
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
 }else if($('#pfFirstAidForm')&&!s.board.autoPaused&&characterIsConscious(s.characters.find(c=>c.id===s.pfEncounter?.character))){
  const mine=s.characters.some(c=>c.id===s.pfEncounter.character&&c.owner===snapshot.me.id);
  message=mine?'La guardiana necesita auxilio. Tú decides si ayudas o esperas; revisa las opciones.':'La guardiana necesita auxilio. El propietario del personaje decide si ayuda o espera.';
  label='Ver opciones de auxilio';open=()=>{chooseTab('story');const target=$('#pfEncounterAid');if(target){target.tabIndex=-1;target.querySelector('h4')?.scrollIntoView({block:'center'});target.focus({preventScroll:true})}};
 }else if(s.board.active){
  const current=s.characters.find(c=>c.id===s.board.order[s.board.turn]?.id);
  message=s.board.autoPaused?'Un turno automático necesita revisión. Consulta el aviso de la mesa.':current?.owner===snapshot.me.id?(characterIsConscious(current)?'Es tu turno. Elige tu acción en el tablero.':'Tu personaje no puede actuar. Revisa su estado en la mesa.'):`Es el turno de ${current?.name||'otro participante'}. Puedes consultar la mesa mientras tanto.`;
  label='Ver el tablero';open=()=>{chooseTab('board');if(current?.owner===snapshot.me.id){$('#boardCharacter').value=current.id;path=[];renderBoard()}$('#board').scrollIntoView({block:'start'});$('#boardCharacter').focus({preventScroll:true})};
 }else if(s.pending.length){
  message=snapshot.me.host?'Hay una situación pendiente de resolución excepcional. Puedes revisarla en el diario.':'El anfitrión tiene una situación pendiente de resolución excepcional.';
  label='Ver pendientes';open=()=>{chooseTab('journal');$('#journalPending').scrollIntoView({block:'center'})};
 }else if($('#pfContinueScene')){
  const ready=!$('#pfContinueScene').disabled;
  message=ready?'Puedes investigar el registro del patio. Decide si continúas o revisas otras opciones.':$('#pfContinueHint')?.textContent||'Revisa el estado del encuentro antes de continuar.';
  label=ready?'Ver cómo investigar':'Revisar cómo continuar';open=()=>{
   chooseTab('story');const target=ready?$('#pfContinueScene'):$('#pfContinueHint');
   if(target){if(!ready)target.tabIndex=-1;target.scrollIntoView({block:'center'});target.focus({preventScroll:true})}
  };
 }else if(s.adventureRouteView?.completed){
  message='Has resuelto el objetivo de la ruta. Puedes revisar los hallazgos o salir y retomarla después.';
  label=s.adventureRouteView.visitedScenes?.length>1?'Revisar hallazgos':'Revisar el diario';open=showRouteFindings;
 }else if(s.adventureRouteView?.exits.length&&s.adventureModuleView?.completed){
  message='La investigación de este lugar está resuelta. Puedes consultar las salidas de la ruta.';
  label='Ver salidas';open=()=>{
   chooseTab('story');const exits=$$('[data-route-exit]'),target=exits.find(b=>!b.disabled)||exits[0]?.closest('.card')?.querySelector('small');
   if(target){if(target.tagName!=='BUTTON')target.tabIndex=-1;target.scrollIntoView({block:'center'});target.focus({preventScroll:true})}
  };
 }else if(s.adventureModuleView&&!s.adventureModuleView.completed){
  const canSearch=!!$('#investigationForm button:not(:disabled)');
  message=canSearch?'Puedes investigar este lugar. Elige qué revisar y cómo buscar.':$('#investigationHelp')?.textContent||'Revisa las opciones de investigación y el estado de tu personaje.';
  label=canSearch?'Ver qué investigar':'Revisar opciones';open=()=>showInvestigationScene(canSearch);
 }else if(s.adventureModuleView?.completed&&s.nextAdventureView?.kind==='group'){
  const proposal=s.nextAdventureView.proposal;
  message=proposal?(proposal.author===snapshot.me.id?'Tu propuesta espera la decisión del otro propietario.':'Hay un objetivo propuesto. Revísalo antes de decidir si continúas.'):'La investigación está resuelta. Podéis elegir juntos el próximo objetivo aquí.';
  label='Ver siguiente objetivo';open=()=>{chooseTab('story');$('#sharedNextAdventure')?.scrollIntoView({block:'center'});const target=$('#acceptAdventureGoal:not(:disabled)')||$('#proposeAdventureGoal:not(:disabled)')||$('#sharedGoalHint');target?.focus({preventScroll:true})};
 }else if(s.adventureModuleView?.completed){
  const next=s.nextAdventureView?.reason===null&&model.aiConfigured;
  message=next?'La investigación está resuelta. Puedes elegir otro objetivo aquí conservando tu personaje y lo descubierto.':'La investigación está resuelta. Puedes revisar lo descubierto y decidir tu siguiente acción.';
  label=next?'Elegir otro objetivo':'Revisar el diario';open=()=>{if(next){chooseTab('story');$('#nextAdventure')?.click()}else chooseTab('journal')};
 }
 panel.hidden=!message;
 if(text.textContent!==message)text.textContent=message;
 if(button.textContent!==label)button.textContent=label;
 button.classList.toggle('primary',!!saved);button.onclick=open||null;
}
function renderCampaignWorld(s){
 let details=$('#campaignWorldJournal');
 if(!details){details=document.createElement('details');details.id='campaignWorldJournal';details.innerHTML='<summary>Personas y lugares conocidos</summary><div id="campaignWorldNotes"></div>';$('#journalOverview').after(details)}
 const world=s.campaignWorldView,known=world&&[...world.npcs,...world.places,...world.relationships].length;
 details.hidden=!known;if(!known)return;
 const section=(title,entries)=>entries.length?`<h3>${title}</h3>${entries.map(item=>`<h4>${esc(item.name)}</h4><p>${esc(item.public||'Todavía no hay notas compartidas.')}</p>`).join('')}`:'';
 $('#campaignWorldNotes').innerHTML=section('Personas',world.npcs)+section('Lugares',world.places)+section('Vínculos',world.relationships.map(link=>({name:link.fromName+' · '+link.toName,public:link.public})))+'<p class="hint">Recuerdos de la historia. La salud, el equipo y las reglas se consultan en las fichas y el registro.</p>';
}
function renderChapterHistory(s){
 let details=$('#chapterHistory');
 if(!details){details=document.createElement('details');details.id='chapterHistory';details.innerHTML='<summary>Investigaciones anteriores</summary><div id="chapterHistoryNotes"></div>';$('#journalOverview').after(details)}
 const history=s.adventureChaptersView;details.hidden=!history?.completed?.length;if(details.hidden)return;
 $('#chapterHistoryNotes').innerHTML=history.completed.map(chapter=>`<h3>${esc(chapter.title)}</h3><p>${esc(chapter.goal)}</p><p>${esc(chapter.conclusion)}</p><details><summary>Pistas confirmadas</summary>${chapter.discoveries.map(clue=>`<p>${esc(clue.text)}</p>`).join('')}</details>`).join('');
}
function renderJournalOverview(s){
 const lists=[['Aliados',s.allies],['Enemigos',s.enemies],['Incógnitas',s.unknowns]].filter(([,items])=>items?.length);
 const unmeasuredActivity=s.adventureRouteView?.visits>1||s.adventureModuleView?.searchActions>0||s.adventureChaptersView?.clockUncertain;
 const knownAnchor=['Comienzo de la aventura','Inicio de la noche del patio'].includes(s.worldTime)||(s.pfNightRestView?.completed&&s.worldTime===s.pfNightRestView.result?.worldTimeAfter);
 const unknownCurrentTime=unmeasuredActivity&&knownAnchor;
 const timeLabel=unknownCurrentTime?'Hora no registrada':s.worldTime;
 const resolved=s.adventureRouteView?.completed?'Ruta completada':!s.adventureRouteView&&s.adventureModuleView?.completed?'Investigación resuelta':'';
 $('#journalOverview').innerHTML=`<h3>Situación actual</h3><p><strong>${esc(s.location)}</strong> · ${esc(timeLabel)}</p><p>${esc(s.goal)}</p>${resolved?`<p class="notice">${esc(resolved)}. Los hallazgos confirmados quedan guardados.</p>`:''}${!s.adventure&&s.objectives.length?`<ul>${s.objectives.map(v=>`<li>${esc(v)}</li>`).join('')}</ul>`:''}${s.notes?`<h4>Notas confirmadas</h4><p>${esc(s.notes)}</p>`:''}${s.adventureRouteView?.visitedScenes?.length>1?`<details class="visited-scene-notes"><summary>Lugares visitados y hallazgos</summary>${s.adventureRouteView.visitedScenes.map(v=>`<h4>${esc(v.location)}</h4>${v.discoveries.length?v.discoveries.map(d=>`<p>${esc(d.text)}</p>`).join(''):'<p>Sin hallazgos confirmados todavía.</p>'}`).join('')}</details>`:''}${lists.length?`<details><summary>Personas e incógnitas</summary>${lists.map(([title,items])=>`<h4>${title}</h4><ul>${items.map(v=>`<li>${esc(v)}</li>`).join('')}</ul>`).join('')}</details>`:''}`;
 renderCampaignWorld(s);
 renderChapterHistory(s);
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
function messageEntry(message){
 const label={rules:'Resolución',director:'Director de IA',scene:'Escena',action:'Acción',dialogue:'Diálogo',ooc:'Fuera de personaje',private:'Privado'}[message.kind]||'Registro';
 const heading=`<div class="speaker">${esc(message.speaker)}${message.kind==='scene'?'':' · '+esc(label)}</div>`;
 const combat=combatMessage(message),content=(combat??checkMessage(message))+recoveryAudit(message)+(combat===null?messageSources(message):'');
 if(message.kind==='rules'&&typeof message.text==='string'&&message.text.startsWith('Iniciativa d20 + modificador declarado: '))return `<article class="message rules initiative-result"><details><summary>Iniciativa · ver tiradas y orden de turnos</summary>${heading}${content}</details></article>`;
 if(message.kind==='rules'&&typeof message.text==='string'&&message.text.startsWith('PNJ preparado desde plantilla verificada: ')){
  const character=snapshot.state.characters.find(c=>message.text.startsWith('PNJ preparado desde plantilla verificada: '+c.name+'.'));
  return `<article class="message rules npc-preparation"><details><summary>${esc(character?.name||'PNJ')} · ficha preparada</summary>${heading}${content}</details></article>`;
 }
 if(message.kind==='rules'&&typeof message.text==='string'&&message.text.startsWith('Personaje creado automáticamente: ')){
  const character=snapshot.state.characters.find(c=>message.text.startsWith('Personaje creado automáticamente: '+c.name+'.'));
  return `<article class="message rules character-preparation"><details><summary>${esc(character?.name||'Personaje')} · ficha preparada</summary>${heading}${content}</details></article>`;
 }
 return `<article class="message ${esc(message.kind)}">${heading}${content}</article>`;
}
function combatMessage(message){
 const result=message.combat;
 if(message.kind!=='rules'||!result||typeof result.hit!=='boolean'||typeof result.critical!=='boolean'||(result.critical&&!result.hit)||!['damage','targetHp','attackerHp'].every(key=>Number.isFinite(result[key]))||typeof result.status!=='string'||typeof result.attackerStatus!=='string')return null;
 const attacker=snapshot.state.characters.find(c=>c.id===result.attacker),target=snapshot.state.characters.find(c=>c.id===result.target);
 const outcome=result.critical?'Crítico confirmado':result.hit?'Impacto':'Fallo';
 return `<p class="combat-result"><strong>${outcome} · ${esc(attacker?.name||'Atacante')} → ${esc(target?.name||'Objetivo')}</strong><br>Daño: ${esc(result.damage)}. ${esc(target?.name||'Objetivo')}: ${esc(result.targetHp)} PG (${esc(result.status)}).${result.attackerHp<=0?`<br>${esc(attacker?.name||'Atacante')}: ${esc(result.attackerHp)} PG (${esc(result.attackerStatus)}).`:''}<br>Acción estándar gastada.</p><details class="combat-audit"><summary>Ver tirada, cálculo y fuentes</summary><p>${esc(message.text)}</p>${messageSources(message)}</details>`;
}
function recoveryAudit(message){
 if(!Array.isArray(message.recoveryChecks)||!message.recoveryChecks.length||message.recoveryChecks.length>40||message.recoveryChecks.some(check=>!check||typeof check!=='object'))return '';
 return `<details class="recovery-audit"><summary>Ver tiradas de recuperación (${message.recoveryChecks.length})</summary>${message.recoveryChecks.map((check,i)=>`<p>${check.characterName?esc(check.characterName)+' · hora '+esc(check.hour):'Hora '+(i+1)}: d20 ${esc(check.die)}, modificador ${esc(check.modifier)}, total ${esc(check.total)} frente a 10. ${check.conscious?'Recupera la consciencia':check.dead?'Muere por sus heridas':'Sigue inconsciente'}. PG: ${esc(check.hpBefore)} → ${esc(check.hpAfter)}.</p>`).join('')}</details>`;
}
function partyPerson(c){
 const s=snapshot.state;
 return `<div class="party-person" role="button" tabindex="0" data-character="${esc(c.id)}"><div class="avatar">${esc(c.name[0])}</div><div><strong>${esc(c.name)}</strong><small>${esc(c.race)} · ${esc(c.class)} ${c.level}</small><div class="hpbar"><span style="width:${Math.max(0,Math.min(100,100*c.hp/c.maxHp))}%"></span></div><small>${c.hp} / ${c.maxHp} PG${characterHealthLabel(c)?' · '+esc(characterHealthLabel(c)):''} · ${esc(c.npcCreation?'Director de la aventura':snapshot.players.find(p=>p.id===c.owner)?.name||'Jugador anterior')}${s.boardScenes&&c.sceneId!==s.boardScenes.current?' · En otra escena':''}</small></div></div>`;
}
function renderParty(s){
 const elsewhere=s.characters.filter(c=>c.enemy&&s.boardScenes&&c.sceneId!==s.boardScenes.current&&!c.conditions?.trim()&&(characterIsConscious(c)||c.hp<=-c.abilities[2]));
 const deferred=new Set(elsewhere.map(c=>c.id)),present=s.characters.filter(c=>!deferred.has(c.id));
 $('#party').innerHTML=present.map(partyPerson).join('')+(elsewhere.length?`<button type="button" id="otherSceneCharacters">En otra escena · ${elsewhere.length}</button>`:'')||'<small>Aún no hay personajes. Crea tu primer aventurero.</small>';
 if($('#otherSceneCharacters'))$('#otherSceneCharacters').onclick=()=>modal(`<div class="eyebrow">OTROS PERSONAJES</div><h2>En otra escena</h2><p>Siguen en la partida, pero sus fichas no están en el tablero actual. Puedes consultarlas sin moverlas.</p>${elsewhere.map(partyPerson).join('')}`);
}
function render(){const importStatus=$('#copyImportStatus'),access=snapshot.id+':'+snapshot.me.id;if(importStatus.dataset.access!==access){importStatus.hidden=true;importStatus.dataset.access=access}if(snapshot.state.ruleset==='rule-pack'){RulePackUI.render();return}if($('#rulePackWorkspace'))$('#rulePackWorkspace').hidden=true;if(snapshot.state.ruleset==='cairn-1e'){$('#campaignTitle').textContent=snapshot.title;$('#campaignMeta').textContent='Cairn 1e';$('#inviteBtn').hidden=!snapshot.me.host;$('#welcome').hidden=true;$('#app').hidden=false;$('#app > .workspace').hidden=true;run(()=>CairnUI.render())();return}if($('#systemWorkspace'))$('#systemWorkspace').hidden=true;$('#app > .workspace').hidden=false;const s=snapshot.state, me=snapshot.me;$('#savedLibraryPanel').hidden=true;$('#welcome').hidden=true;$('#app').hidden=false;$('#campaignTitle').textContent=snapshot.title;$('#campaignMeta').textContent=`Pathfinder 1e · ${snapshot.players.length} ${snapshot.players.length===1?'jugador':'jugadores'} · ${s.characters.length} ${s.characters.length===1?'personaje':'personajes'}`;$('#place').textContent=s.location;$('#objective').textContent=s.goal;$('#sceneNum').textContent=s.scene;$('#tokenNum').textContent=`${s.tokens} / ${s.threshold}`;$('#phase').textContent=s.turned?'Punto de giro alcanzado · desenlace':'Desarrollo de la aventura';$('#sceneTitle').textContent=`Escena ${s.scene} · ${s.location}`;
 renderParty(s);renderDiceEntry();
 const available=s.characters.filter(c=>me.host||c.owner===me.id), boardPrev=$('#boardCharacter').value;
 renderSpeakerChoices();
 const boardAvailable=boardCharacters(s).filter(c=>me.host||c.owner===me.id);
 $('#boardCharacter').innerHTML=boardAvailable.map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join('');if(boardAvailable.some(c=>c.id===boardPrev))$('#boardCharacter').value=boardPrev;
 const area=$('#story'), near=area.scrollHeight-area.scrollTop-area.clientHeight<150;
 $('#messages').innerHTML=s.messages.map(messageEntry).join('');
 if(!available.length)$('#messages').insertAdjacentHTML('afterbegin','<div class="card"><div class="eyebrow">PASO 1 · TU PERSONAJE</div><h3>¿Quién vivirá esta aventura?</h3><p>Elige un estilo y un nombre. El creador calcula tu ficha; después podrás elegir la aventura.</p><button class="primary" data-create-hero>Crear mi personaje</button></div>');
 document.body.classList.toggle('preparing-adventure',!s.adventure&&!s.pfEncounter&&!s.board.active&&s.location==='Por decidir');document.body.classList.toggle('adventure-active',!!(s.adventure||s.pfEncounter));renderAdventure();renderChecks();renderPlayGuidance(s);
 if(s.pfEncounter?.phase==='offered'){
  const opening=snapshot.id+':'+s.pfEncounter.character+':'+s.pfEncounter.definition.version;
  if(area.dataset.offeredEncounter!==opening)area.scrollTop=0;
  area.dataset.offeredEncounter=opening;
 }else{
  delete area.dataset.offeredEncounter;const last=s.messages.at(-1);
  if(last?.adventureStart||last?.adventureChapterStart){
   const introduction=snapshot.id+':'+(last.preparedOpeningSha256||last.time)+':'+last.kind;
   if(area.dataset.adventureIntroduction!==introduction){area.scrollTop=0;if(area.classList.contains('active'))showAdventureIntroduction(false)}
   area.dataset.adventureIntroduction=introduction;
  }else{delete area.dataset.adventureIntroduction;if(near)area.scrollTop=area.scrollHeight;}
 }
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
function renderBoard(){if(!snapshot)return;renderAttack();renderAutomation();const s=snapshot.state,board=s.board;const title=s.boardScenes||s.adventureModuleView||s.pfEncounter?s.location:board.active?'Encuentro':'Tu mesa';$('#board .eyebrow').textContent=board.active?'ENCUENTRO':'LA MESA';if($('#board h2').textContent!==title)$('#board h2').textContent=title;$('#turnInfo').textContent=board.active?`Asalto ${board.round} · Turno de ${s.characters.find(c=>c.id===board.order[board.turn].id)?.name} · ${board.order.map(o=>s.characters.find(c=>c.id===o.id)?.name+' '+(o.roll+o.modifier)).join(' → ')}`:'Exploración · sin combate activo';
 const grid=$('#grid'),focused=document.activeElement?.closest('#grid .cell'),visible=boardCharacters(s),focusKey=snapshot.id+':'+snapshot.me.id+':'+(s.boardScenes?.current||'main');
 if(gridFocusKey!==focusKey){
  const selected=visible.find(c=>c.id===$('#boardCharacter').value);gridFocus=[selected?.x??0,selected?.y??0].map(n=>Number.isInteger(n)?Math.max(0,Math.min(19,n)):0);gridFocusKey=focusKey;
 }else if(focused)gridFocus=[Number(focused.dataset.x),Number(focused.dataset.y)];
 grid.setAttribute('aria-label','Tablero de '+s.location+'. Flechas para recorrer casillas; Intro utiliza la herramienta elegida.');
 let cells='';
 for(let y=0;y<20;y++)for(let x=0;x<20;x++){
  const c=visible.find(c=>c.x===x&&c.y===y),terrain=board.terrain[x+','+y],current=c&&board.active&&board.order[board.turn]?.id===c.id;
  const label=`Casilla ${x},${y}${terrain==='wall'?'. Muro':terrain==='difficult'?'. Terreno difícil':''}${c?'. '+c.name+', '+c.hp+' PG'+(characterHealthLabel(c)?', '+characterHealthLabel(c):''):''}${current?'. Turno actual':''}`;
  cells+=`<button class="cell ${terrain||''} ${path.some(p=>p[0]===x&&p[1]===y)?'path':''} ${ruler.some(p=>p[0]===x&&p[1]===y)?'measured':''} ${current?'current-turn':''}" tabindex="${gridFocus[0]===x&&gridFocus[1]===y?'0':'-1'}" data-token-id="${esc(c?.id||'')}" data-controlled="${!!c&&(snapshot.me.host||c.owner===snapshot.me.id)}" aria-pressed="${!!c&&c.id===$('#boardCharacter').value}" data-x="${x}" data-y="${y}" aria-label="${esc(label)}">${c?`<span class="token ${c.enemy?'enemy':''}">${esc(c.name.slice(0,2))}</span><span class="token-hp">${c.hp} PG</span>`:''}</button>`;
 }
 grid.innerHTML=cells;
 if(focused)grid.querySelector(`.cell[data-x="${gridFocus[0]}"][data-y="${gridFocus[1]}"]`)?.focus({preventScroll:true});
 let c=s.characters.find(c=>c.id===$('#boardCharacter').value),x=c?.x,y=c?.y,diagonal=0,cost=0;for(const [nx,ny] of path){let d=nx!==x&&ny!==y;if(d)diagonal++;cost+=board.terrain[nx+','+ny]==='difficult'?(d?3:2):(d&&diagonal%2===0?2:1);x=nx;y=ny}$('#pathInfo').textContent=path.length?`Recorrido: ${path.map(p=>p.join(',')).join(' → ')} · Coste: ${cost*5} pies (${cost} casillas). Revisión manual de AdO, alcance, visibilidad y consecuencias antes de confirmar.`:'Selecciona una ficha y traza casillas adyacentes.';renderTabletopTools()}
function openBook(book=$('#book').value,page=Number($('#page').value)){if(!token)return;$('#book').value=book;$('#page').value=page;bookReader.open(book,page)}
function fiveFootStepReason(c){
 const s=snapshot.state,b=s.board,r=s.pfEncounter,opponent=s.characters.find(v=>v.id===r?.npc);
 if(!b.active||r?.phase!=='combat'||s.mode!=='solo'||s.characters.length!==2||c?.id!==r.character||c.owner!==snapshot.me.id)return 'Solo el propietario puede dar el paso con su personaje durante este combate.';
 if(b.autoPaused)return 'Resuelve primero la pausa del turno automático.';
 if(b.order[b.turn]?.id!==c.id)return 'Espera al turno de tu personaje.';
 if(!characterIsConscious(c)||!opponent||!boardCharacters(s).includes(c)||!boardCharacters(s).includes(opponent))return 'Revisa primero el estado de las fichas.';
 if(c.conditions?.trim()||opponent.conditions?.trim()||r.definition.conditions?.lighting!=='normal'||s.pending.length||s.consequences.some(e=>!e?.interpreted))return 'Resuelve primero las condiciones o situaciones pendientes.';
 if(!Number.isInteger(c.speed)||c.speed<=1)return 'Necesitas una velocidad terrestre superior a 5 pies.';
 if(b.fiveFootSteps?.[c.id])return 'Ya has dado tu paso: puedes usar las demás acciones disponibles o terminar el turno.';
 if(b.spent[c.id]?.move)return 'Ya hay una acción de movimiento registrada. Si no hubo desplazamiento, usa la revisión excepcional.';
 if(path.length!==1)return 'Para el paso de 5 pies, elige una única casilla adyacente despejada.';
 const [x,y]=path[0],dx=Math.abs(x-c.x),dy=Math.abs(y-c.y),terrain=b.terrain;
 if(x<0||x>=20||y<0||y>=20||Math.max(dx,dy)!==1)return 'Elige una casilla adyacente del tablero.';
 if([terrain[c.x+','+c.y],terrain[x+','+y]].some(v=>v&&v!=='clear'))return 'Este paso automático necesita origen y destino despejados.';
 if(dx&&dy&&(terrain[c.x+','+y]==='wall'||terrain[x+','+c.y]==='wall'))return 'No puedes cortar la esquina de un muro.';
 if(boardCharacters(s).some(v=>v.id!==c.id&&v.x===x&&v.y===y))return 'La casilla está ocupada.';
 return '';
}
function renderTabletopTools(){
 const board=snapshot.state.board,selected=$('#boardCharacter').value,spent=board.spent[selected]||{};
 $('#actionBudget').hidden=!board.active;
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
 const stepEnabled=snapshot.state.pfEncounter?.definition.fiveFootStepScope==='normal-light-ground-five-foot-step-1',stepped=stepEnabled&&board.fiveFootSteps?.[selected];
 $('#confirmMove').textContent=stepEnabled?'Mover con revisión':'Confirmar recorrido';
 $('#confirmMove').classList.toggle('primary',!stepEnabled);
 $('#confirmStep').hidden=!stepEnabled||!board.active||!path.length||$('#tool').value!=='move';
 const stepReason=stepEnabled?fiveFootStepReason(moving):'';
 $('#confirmStep').disabled=!!stepReason;
 if(stepped){$('#confirmMove').disabled=true;$('#actionBudget').textContent+=' · Paso de 5 pies usado; sin más desplazamientos este asalto.';}
 if(!$('#confirmStep').hidden)$('#pathInfo').textContent=stepReason||'Paso de 5 pies: no provoca ataques de oportunidad ni gasta acciones. Después no podrás desplazarte más este asalto. Elige cómo mover.';
 $('#movementPreview').classList.toggle('prepared',!!path.length&&$('#tool').value==='move');
 $('#board').classList.toggle('preparing-move',!!path.length&&$('#tool').value==='move'&&!$('.board-scroll').classList.contains('dragging-token'));
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
 $('#startCombat').hidden=!snapshot.me.host||board.active||snapshot.state.pfEncounter?.phase==='offered'||boardCharacters(snapshot.state).length<2;
 $('#startCombat').disabled=boardCharacters(snapshot.state).length<2;
 $('#endCombat').hidden=!snapshot.me.host||!board.active;
 $('#manualBtn').hidden=!snapshot.me.host;
 $('#autoEnemies').closest('label').hidden=!snapshot.me.host;
 const current=board.active&&snapshot.state.characters.find(c=>c.id===board.order[board.turn]?.id);
 $('#nextTurn').hidden=!board.active;
 $('#nextTurn').disabled=!current||(!snapshot.me.host&&current.owner!==snapshot.me.id);
 const mine=current&&(snapshot.me.host||current.owner===snapshot.me.id);
 let guidance=!snapshot.state.characters.length?'Usa «Crear personaje» para empezar.':!board.active?'Puedes consultar el mapa, medir o preparar un recorrido. El combate solo empieza cuando lo decides.':!mine?`Es el turno de ${current?.name||'otro participante'}. Puedes consultar el mapa mientras esperas.`:current.id!==selected?`Es el turno de ${current.name}. Selecciona su ficha para actuar.`:(spent.standard&&spent.move||current.hp<=0&&(spent.standard||spent.move))?'Ya has usado tus acciones disponibles. Pulsa «Terminar turno» cuando quieras continuar.':spent.standard?'Ya has usado tu acción estándar. Puedes moverte o terminar el turno.':spent.move?'Ya te has movido. Puedes atacar a un objetivo cercano o terminar el turno.':'Es tu turno. Puedes preparar un movimiento, elegir un objetivo para atacar o terminar el turno.';
 if(mine&&current.id===selected&&stepEnabled){
  if(stepped)guidance=spent.standard?'Ya has dado el paso y usado tu acción estándar. Puedes terminar el turno.':'Ya has dado el paso. Puedes atacar a un objetivo cercano o terminar el turno; no puedes desplazarte más este asalto.';
  else if(spent.standard&&!spent.move)guidance='Ya has usado tu acción estándar. Puedes preparar un paso de 5 pies en una casilla despejada o terminar el turno.';
 }
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
 const opponents=boardCharacters(s).filter(c=>source&&c.enemy!==source.enemy),targets=opponents.filter(c=>c.hp>0);
 const targetLimit=!opponents.length?'No hay un adversario presente en esta escena. Revisa el tablero.':opponents.some(c=>characterIsConscious(c))?'El adversario sigue consciente a 0 PG o menos. Esta versión requiere una resolución excepcional para atacarlo. Revisa su ficha o termina tu turno.':'El adversario está caído. Atacarlo requiere una resolución excepcional; revisa su ficha y las opciones de la aventura.';
 $('#attackTarget').innerHTML=targets.map(c=>`<option value="${esc(c.id)}">${esc(c.name)} · ${c.hp} PG</option>`).join('')||`<option value="" disabled selected>${opponents.length===1?esc(opponents[0].name)+' · '+opponents[0].hp+' PG · revisión excepcional':'Sin adversarios disponibles'}</option>`;
 if(targets.some(c=>c.id===previous))$('#attackTarget').value=previous;
 const current=board.active&&board.order[board.turn]?.id===selected;
 const spent=board.spent[selected]||{};
 const target=targets.find(c=>c.id===$('#attackTarget').value),adjacent=source&&target&&Math.max(Math.abs(source.x-target.x),Math.abs(source.y-target.y))===1;
 const disabledMove=source?.hp<=0&&spent.move;
 $('#attackForm').hidden=!board.active;
 $('#attackButton').disabled=!current||!source?.meleeProfile||!characterIsConscious(source)||spent.standard||disabledMove||!adjacent;
 $('#attackButton').textContent=source?.hp<=0&&characterIsConscious(source)?'Atacar · perderás 1 PG':'Tirar ataque y resolver';
 $('#attackHint').textContent=!board.active?'El ataque estará disponible durante un combate.':!current?'Selecciona el personaje de tu turno.':!characterIsConscious(source)?'Tu personaje no puede atacar mientras está inconsciente.':!source?.meleeProfile?'El arma necesita un perfil preparado antes del combate.':spent.standard?'Ya has atacado o usado tu acción estándar. Puedes terminar el turno.':disabledMove?'Estás incapacitado y ya te has movido; termina el turno.':!targets.length?targetLimit:!adjacent?'Acércate a una casilla junto al objetivo para atacar cuerpo a cuerpo.':source.hp<=0?'Si atacas, perderás 1 PG al terminar y '+(source.hp-1<=-source.abilities[2]?'morirás por tus heridas.':'volverás a quedar moribundo. El movimiento no causa esa pérdida de PG.'):'El juego tira, calcula el impacto y aplica el daño. No tienes que calcular modificadores.';
}
$('#attackTarget').onchange=renderAttack;
function showAttackResult(action){
 chooseTab('story');
 const index=snapshot.state.messages.findLastIndex(m=>m.combat?.attacker===action.character&&m.combat.target===action.target),result=$('#messages').children[index]?.querySelector('.combat-result');
 if(result){result.tabIndex=-1;result.scrollIntoView({block:'center'});result.focus({preventScroll:true})}
}
$('#attackForm').onsubmit=run(async()=>{
 const action={character:$('#boardCharacter').value,target:$('#attackTarget').value};
 await showActionResult('attack',action,()=>showAttackResult(action));
});
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
async function enterCampaign(form,url,config){
 ensureCampaignCanChange();
 const button=form.querySelector('button'),label=button.textContent;let opened=false;
 busy=true;button.disabled=true;button.textContent='Abriendo partida…';renderComposerAvailability();
 try{
  const result=await api(url,config);token=result.token;localStorage.setItem('cronicas-token',token);opened=true;
  if(url==='/api/join'){
   const address=new URL(location.href);address.searchParams.delete('invite');history.replaceState(history.state,'',address.pathname+address.search+address.hash);prepareEntryInvitation(null);
  }
  await refresh(true);
 }catch(error){if(opened&&snapshotToken!==token)throw Error('Tu acceso se ha guardado en este navegador. Pulsa «Continuar mi última campaña» para cargar la partida. '+error.message);throw error}
 finally{busy=false;button.disabled=false;button.textContent=label;$('#resume').hidden=!token;renderComposerAvailability()}
}
$('#createForm').onsubmit=run(async e=>{const config=values(e.target);config.player=config.player.trim();if(!config.player)throw Error('Escribe tu nombre para empezar.');config.goal=config.goal.trim()||'Descubrir una aventura.';config.title=config.title.trim()||'Mi aventura';await enterCampaign(e.target,'/api/create',config)});
$('#joinForm').onsubmit=run(async e=>{await enterCampaign(e.target,'/api/join',values(e.target))});
$('#libraryBtn').onclick=run(()=>openCampaignLibrary());$('#manageAccesses').onclick=run(()=>openCampaignLibrary());$('#resume').onclick=run(async()=>{if(busy)throw Error('Espera a que termine la operación actual antes de volver a la partida.');busy=true;$('#resume').disabled=true;try{await refresh(true)}finally{busy=false;$('#resume').disabled=false;renderComposerAvailability()}});$('#exitBtn').onclick=run(async()=>{ensureCampaignCanChange();bookReader.reset();document.body.classList.remove('reader-wide');$('#app').hidden=true;$('#welcome').hidden=false;$('#resume').hidden=!token;$('#savedLibraryPanel').hidden=false;renderSavedCampaigns()});
$('#inviteBtn').onclick=run(async()=>{const link=location.origin+'/?invite='+encodeURIComponent(snapshot.invite);modal('<h2>Reunir al grupo</h2><p>Comparte este código con quienes tengan acceso al servidor. El nombre de jugador no sustituye la credencial de reconexión guardada en su navegador.</p><label>Código<input readonly value="'+esc(snapshot.invite)+'"></label><label>Enlace<input readonly value="'+esc(link)+'"></label><p class="hint">127.0.0.1 solo abre en este ordenador. Para red local inicia con HOST=0.0.0.0 y usa la dirección del servidor. Para Internet se requiere alojamiento, HTTPS y configuración de acceso.</p>')});
$('#addCharacter').onclick=()=>characterForm();$('#manualBtn').onclick=()=>manualForm();
$('#composer').addEventListener('input',()=>{messageRevision++});
$('#composer').addEventListener('change',()=>{messageRevision++});
$('#composer').onsubmit=run(async()=>{
 const reason=conversationUnavailable();if(reason)throw Error(reason);
 const text=$('#message').value,revision=messageRevision,access=token;
 const data={text,character:$('#speaker').value||null,kind:$('#messageKind').value,director:$('#useAI').checked&&$('#messageKind').value!=='private'};
 await showActionResult('talk',data,()=>{if($('#story').classList.contains('active'))$('#story').scrollTop=$('#story').scrollHeight});
 if(token===access&&revision===messageRevision&&$('#message').value===text)$('#message').value='';
 submittedMessage=undefined;
});
$('#message').onkeydown=e=>{if(e.ctrlKey&&e.key==='Enter'){e.preventDefault();if(!$('#send').disabled)$('#composer').requestSubmit()}};
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
function rememberGridFocus(cell){
 if(!cell)return;const previous=$('#grid .cell[tabindex="0"]');
 if(previous!==cell)previous?.setAttribute('tabindex','-1');cell.tabIndex=0;gridFocus=[Number(cell.dataset.x),Number(cell.dataset.y)];
}
$('#grid').addEventListener('focusin',e=>rememberGridFocus(e.target.closest('.cell')));
$('#grid').onkeydown=e=>{
 const step={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key],cell=e.target.closest('.cell');
 if(!step||!cell||e.ctrlKey||e.altKey||e.metaKey||e.shiftKey||$('#modal').open||$('#app').hidden)return;
 e.preventDefault();const x=Math.max(0,Math.min(19,Number(cell.dataset.x)+step[0])),y=Math.max(0,Math.min(19,Number(cell.dataset.y)+step[1]));
 const next=$(`#grid .cell[data-x="${x}"][data-y="${y}"]`);rememberGridFocus(next);next?.focus();
};
$('#grid').onclick=run(async e=>{const cell=e.target.closest('[data-x]');if(!cell)return;const x=+cell.dataset.x,y=+cell.dataset.y,tool=$('#tool').value;if(tool==='pan')return;if(tool==='measure'){ruler=ruler.length===1?[ruler[0],[x,y]]:[[x,y]];renderBoard();return}if(tool!=='move'){await act('terrain',{x,y,terrain:tool});return}const clicked=boardCharacters(snapshot.state).find(c=>c.x===x&&c.y===y);if(clicked){if(!preparedOpponentTarget(clicked)&&(snapshot.me.host||clicked.owner===snapshot.me.id)){if($('#boardCharacter').value!==clicked.id||path.length){$('#boardCharacter').value=clicked.id;path=[];renderBoard()}}else{$('#attackTarget').value=clicked.id;renderAttack();toast('Objetivo seleccionado: '+clicked.name)}return}const ch=snapshot.state.characters.find(c=>c.id===$('#boardCharacter').value);if(!ch)throw Error('Crea y selecciona una ficha');let prev=path.length?path[path.length-1]:[ch.x,ch.y];if(Math.max(Math.abs(prev[0]-x),Math.abs(prev[1]-y))!==1)throw Error('Selecciona una casilla adyacente al último punto');path.push([x,y]);renderBoard()});
function preparedOpponentTarget(character){
 const s=snapshot.state,encounter=s.pfEncounter;
 return s.mode==='solo'&&s.board.active&&encounter?.phase==='combat'&&character.id===encounter.npc&&$('#boardCharacter').value===encounter.character&&s.characters.some(c=>c.id===encounter.character&&c.owner===snapshot.me.id);
}
$('#clearPath').onclick=()=>{path=[];renderBoard()};
$('#confirmStep').onclick=run(async()=>{
 ensureSubmissionCanStart();
 const characterId=$('#boardCharacter').value,c=snapshot.state.characters.find(v=>v.id===characterId),reason=fiveFootStepReason(c);
 if(reason)throw Error(reason);
 const action=$('#confirmStep'),returnFocus=action.matches(':focus-visible');
 await act('five_foot_step',{character:characterId,path});
 if(returnFocus&&(document.activeElement===action||document.activeElement===document.body)){
  const moved=boardCharacters(snapshot.state).find(v=>v.id===characterId),cell=moved&&$(`#grid .cell[data-x="${moved.x}"][data-y="${moved.y}"]`);rememberGridFocus(cell);cell?.focus();
 }
});
$('#confirmMove').onclick=run(async()=>{
 ensureSubmissionCanStart();
 if(!path.length)throw Error('Traza un recorrido primero');
 const action=$('#confirmMove'),returnFocus=action.matches(':focus-visible'),characterId=$('#boardCharacter').value;
 if(!confirm($('#pathInfo').textContent+'\n¿Has revisado las consecuencias conocidas y las reglas pendientes con la mesa?'))return;
 await act('move',{character:characterId,path,acknowledge:true});
 if(returnFocus&&(document.activeElement===action||document.activeElement===document.body)){
  const c=boardCharacters(snapshot.state).find(c=>c.id===characterId),cell=c&&$(`#grid .cell[data-x="${c.x}"][data-y="${c.y}"]`);rememberGridFocus(cell);cell?.focus();
 }
});
$('#openPage').onclick=()=>openBook();$('#book').onchange=()=>openBook($('#book').value,1);$('#bookmark').onclick=run(async()=>{const label=prompt('Nombre del marcador',names[$('#book').value]+' · p.'+$('#page').value);if(label)await act('bookmark',{book:$('#book').value,page:+$('#page').value,label})});
async function find(q){const data=await api('/api/search?q='+encodeURIComponent(q)+'&book='+$('#book').value);$('#searchResults').innerHTML=data.map(r=>`<div class="result">${ref(r.book,r.page)}<p>${esc(r.text)}</p></div>`).join('')||'<p>No hay coincidencias fiables en el texto extraído. Consulta el original; puede requerir OCR.</p>'}
$('#searchForm').onsubmit=run(()=>find($('#searchQuery').value));$('#indexBtn').onclick=run(()=>find('índice contenido'));$('#askRule').onclick=run(async()=>{$('#ruleAnswer').textContent='Consultando fuentes y servicio de IA…';try{let r=await api('/api/rules',{q:$('#searchQuery').value});$('#ruleAnswer').innerHTML='<p>'+esc(r.answer)+'</p>'+r.refs.map(v=>ref(v.book,v.page)).join('')}catch(e){$('#ruleAnswer').textContent=e.message}});
$('#exportBtn').onclick=run(async()=>{const data=await api('/api/export',{});let url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));let a=document.createElement('a');a.href=url;a.download='cronica-'+snapshot.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
$('#importFile').onchange=run(async e=>{
 const file=e.target.files[0];if(!file)return;
 const status=$('#copyImportStatus'),sourceAccess=token,sourceCampaign=snapshot.id;status.hidden=true;
 let campaign;
 try{campaign=JSON.parse(await file.text());if(!campaign||Array.isArray(campaign)||campaign.format!=='cronicas-1')throw Error('Formato incompatible')}
 catch{if(token!==sourceAccess||snapshot.id!==sourceCampaign){e.target.value='';throw Error('La partida ha cambiado. Elige de nuevo la copia en la partida que quieras recuperar.')}status.textContent='No se puede leer esta copia. Tu partida sigue como estaba. Elige una copia de partida guardada desde esta aplicación.';status.hidden=false;e.target.value='';throw Error('No se puede leer la copia. Elige otro archivo.')}
 if(token!==sourceAccess||snapshot.id!==sourceCampaign){e.target.value='';throw Error('La partida ha cambiado. Elige de nuevo la copia en la partida que quieras recuperar.')}
 const sameCampaign=(!snapshot.state.ruleset||snapshot.state.ruleset==='pathfinder-1e')&&campaign.sourceCampaignId===snapshot.id;
 const ownership=sameCampaign?'Los personajes conservarán a sus propietarios si siguen en esta sala; los demás se asignarán al anfitrión.':'Los personajes se asignarán al anfitrión que importa.';
 const pendingGoal=campaign.state?.chapterGoalProposal?' El objetivo de grupo todavía pendiente deberá elegirse de nuevo.':'';
 if(!confirm('La copia sustituirá tu partida actual. '+ownership+pendingGoal+' Guarda antes una copia si quieres conservar el estado actual.')){e.target.value='';status.textContent='Recuperación cancelada. Tu partida sigue como estaba.';status.hidden=false;return;}
 try{await act(sameCampaign?'restore_campaign_copy':'import',{campaign});status.textContent='Copia recuperada. Puedes continuar con tu partida.';status.hidden=false;toast('Copia recuperada')}
 catch(error){
  if(error.status===400){status.innerHTML='<p>La copia no es compatible. Tu partida sigue como estaba. Prueba con otra copia.</p><details><summary>Ver el motivo</summary><p>'+esc(error.message)+'</p></details>';status.hidden=false;throw Error('Copia rechazada. Tu partida sigue como estaba.')}
  throw error;
 }finally{e.target.value=''}
});
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
async function init(){renderSavedCampaigns();const invite=new URLSearchParams(location.search).get('invite');prepareEntryInvitation(invite);try{model=await api('/api/status');await loadSystemChoices();$('#capabilities').innerHTML=`<p><strong>● Guardado persistente</strong><br>${esc(model.storage)}</p><p>${model.aiConfigured?'● IA configurada: '+esc(model.model):'○ Director de IA sin configurar'}<br>Conexión real a Claude Haiku; sin respuestas prefijadas.</p><p>${Object.entries(model.books).map(([k,n])=>esc(names[k])+': '+n+' páginas indexadas').join('<br>')}</p>`;$('#aiHint').textContent=model.aiConfigured?'El director responderá si activas «Responder con IA». Las tiradas y herramientas funcionan sin IA.':'El director no está disponible en esta mesa. Puedes usar las fichas, los dados y el tablero sin IA.';$('#askRule').disabled=!model.aiConfigured;$('#ruleAIHint').textContent=model.aiConfigured?'Consultar a la IA usa el servicio del director. Buscar en el texto y leer páginas no llama a IA.':'El director no está disponible. Puedes buscar en el texto y leer el manual.';$('#useAI').disabled=!model.aiConfigured;if(!model.aiConfigured)$('#useAI').checked=false;$('#resume').hidden=!token;try{await withSubmissionLock(()=>{})}catch(error){toast(error.message)}if(token&&!invite){let accepted;const pending=JSON.parse(localStorage.getItem('cronicas-pending')||'null');if(pending&&pending.token===token){try{busy=true;accepted=await recoverSubmission(pending)}catch(e){if(e.confirmed)await clearSubmission(pending);toast(e.message)}finally{busy=false}}await refresh(true);if(accepted){await clearSubmission(accepted);if(token===accepted.token){renderSyncStatus();renderComposerAvailability();renderSubmissionFeedback();toast('Envío recuperado')}}}}catch(e){toast(e.message)}}
const tabletopControls=window.TabletopControls.mount({
 scroller:$('.board-scroll'),grid:$('#grid'),tool:$('#tool'),zoom:$('#zoom'),snapshot:()=>snapshot&&(!snapshot.state.ruleset||snapshot.state.ruleset==='pathfinder-1e')?{...snapshot,state:{...snapshot.state,characters:boardCharacters(snapshot.state)}}:null,
 select:id=>{$('#boardCharacter').value=id;path=[];renderBoard()},
 preview:points=>{path=points;renderBoard()},measure:points=>{ruler=points;renderBoard()},
 cancel:()=>{path=[];ruler=[];if(snapshot&&(!snapshot.state.ruleset||snapshot.state.ruleset==='pathfinder-1e'))renderBoard()},openSheet:characterForm,tab:chooseTab,
 focusChat:()=>$('#message').focus(),notify:toast,gestureEnd:()=>renderTabletopTools(),repaint:()=>{if(snapshot&&(!snapshot.state.ruleset||snapshot.state.ruleset==='pathfinder-1e'))renderBoard()}
});
let readerExpanded=false;
const bookReader=window.BookReader.mount({token:()=>token,image:$('#bookPageImage'),status:$('#bookLoadStatus'),input:$('#page'),total:$('#bookPageTotal'),previous:$('#previousBookPage'),next:$('#nextBookPage')});
$('#previousBookPage').onclick=()=>openBook($('#book').value,Number($('#page').value)-1);
$('#nextBookPage').onclick=()=>openBook($('#book').value,Number($('#page').value)+1);
$('#readerZoomOut').onclick=()=>bookReader.zoom(-25);
$('#readerZoomIn').onclick=()=>bookReader.zoom(25);
$('#readerFit').onclick=()=>bookReader.fit();
$('#expandReader').onclick=()=>{readerExpanded=!readerExpanded;renderReaderMode()};
window.addEventListener('storage',event=>{if(event.key==='cronicas-pending'&&snapshot&&!busy){renderSyncStatus();renderComposerAvailability();renderSubmissionFeedback()}});
let syncing=false;
async function syncVisible(){
 if(!token||document.hidden||$('#app').hidden||busy||syncing)return;
 syncing=true;
 try{await refresh()}catch{$('#sync').textContent='Sin conexi\u00f3n - reintentando'}finally{syncing=false}
}
setInterval(syncVisible,15000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)syncVisible()});
init();
