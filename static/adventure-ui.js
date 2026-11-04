/* Adventure preparation is an explicit action; rendering and reading stay local. */
function renderAdventure(){
 const s=snapshot.state, host=!!snapshot.me.host, active=!!s.adventure;
 const ready=s.characters.some(c=>!c.enemy&&c.creation&&!c.creation.manualOverride&&c.hp>0&&!c.conditions?.trim());
 const entry=$('#adventureEntry');
 entry.hidden=active;
 entry.innerHTML=active?'':`<div class="card"><div class="eyebrow">LA PRIMERA PÁGINA</div><h3>El mundo espera a tu personaje</h3><p>${host?'La IA preparará un comienzo, personajes y secretos a partir de la premisa de tu campaña. Después, tú decides cómo actuar.':'El anfitrión puede iniciar la aventura cuando haya un personaje listo.'}</p>${host?`<button id="beginAdventure" class="primary" ${!ready||!model.aiConfigured||s.board.active?'disabled':''}>Iniciar aventura con IA</button><small>${!ready?'Crea primero un personaje con el asistente.':!model.aiConfigured?'Falta configurar el director de IA.':s.board.active?'Finaliza el combate para comenzar.':'El comienzo se guarda para continuar en otra sesión.'}</small>`:''}</div>`;
 if($('#beginAdventure'))$('#beginAdventure').onclick=()=>{
  modal(`<div class="eyebrow">UN NUEVO COMIENZO</div><h2>¿Qué historia te apetece vivir?</h2><form id="adventureForm"><label>Premisa<textarea name="premise" required maxlength="2000" rows="4">${esc(s.goal)}</textarea></label><p>El director respetará el tono y los límites de tu campaña. Preparará la aventura sin decidir las acciones de tu personaje.</p><button class="primary">Preparar y comenzar</button><p id="adventureProgress" role="status" aria-live="polite"></p><small>Se utiliza la IA configurada. El combate y las reglas aún tienen cobertura limitada.</small></form>`);
  $('#adventureForm').onsubmit=run(async e=>{
   const form=e.target,button=form.querySelector('button');button.disabled=true;
   $('#adventureProgress').textContent='El director está preparando la aventura…';
   try{await act('start_adventure',values(form));$('#modal').close();chooseTab('story');}
   catch(error){$('#adventureProgress').textContent=error.message;throw error;}
   finally{button.disabled=false;}
  });
 };
 const memory=$('#adventureMemory');memory.hidden=!active;
 $('#adventureSummary').textContent=s.adventure?.summary||'';
 $('#adventureObjectives').innerHTML=(s.objectives||[]).map(item=>`<li>${esc(item)}</li>`).join('');
 $('#adventureRevision').textContent=active?`Memoria narrativa del director · revisión ${s.adventure.revision}. Las tiradas y sus consecuencias se consultan en el registro.`:'';
 const privateMemory=$('#directorMemoryDetails');privateMemory.hidden=!host||!s.directorMemory;
 $('#directorMemoryText').textContent=host?s.directorMemory||'':'';
 const lastDirector=s.messages.findLastIndex(m=>m.kind==='director'&&!m.ooc);
 const results=s.messages.filter((m,i)=>i>lastDirector&&m.check);
 const ownsResult=host||results.some(m=>s.characters.some(c=>c.id===m.check.character&&c.owner===snapshot.me.id));
 const continuation=$('#continueAdventure');
 continuation.hidden=!active||!results.length||!ownsResult||s.pending.some(p=>p.check);
 continuation.disabled=!model.aiConfigured;
 continuation.onclick=run(()=>act('continue_adventure'));
}
