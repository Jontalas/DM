/* Step-by-step local creation; exactly one campaign action when confirmed. */
let creationCatalog,creatorGeneration=0;
document.addEventListener('click',e=>{if(e.target.closest('[data-create-hero]'))characterForm()});
async function getCreationCatalog(){
 if(!creationCatalog)creationCatalog=fetch('/creation-catalog.json?v=1').then(r=>{if(!r.ok)throw Error('No se pudo cargar el creador');return r.json()}).catch(e=>{creationCatalog=null;throw e});
 return creationCatalog;
}
function characterForm(cid,afterCreation=false){
 if(!cid){run(()=>startCharacterCreator())();return}
 const c=snapshot.state.characters.find(v=>v.id===cid),prepared=!!c?.npcCreation;
 if(!prepared&&(!c?.creation||c.creation.manualOverride)){manualCharacterForm(cid);return}
 const d=c.creation?.details,mayEdit=snapshot.me.host||c.owner===snapshot.me.id;
 const editReason=!mayEdit?(prepared?'Solo el anfitrión puede registrar una corrección excepcional de este PNJ.':'Esta ficha pertenece a otro jugador. Su propietario o el anfitrión pueden corregirla.'):snapshot.state.board.active?'La edición manual está bloqueada durante el combate. Usa las acciones de la mesa y vuelve al terminar.':prepared?'Solo para una excepción. Guardar cambios registrará una corrección sobre la plantilla de la aventura.':'Solo para corregir una excepción. Editar manualmente deja esta ficha fuera del cálculo automático.';
 const canBegin=afterCreation&&!prepared&&!c.enemy&&snapshot.me.host&&$('#beginAdventure')&&!$('#beginAdventure').disabled;
 const onBoard=boardCharacters(snapshot.state).some(character=>character.id===c.id),boardScope={access:token,campaign:snapshot.id,player:snapshot.me.id};
 const boardLink=afterCreation?'':`${onBoard?'<button type="button" id="showCharacterOnBoard" aria-describedby="characterBoardHint">Ver en el tablero</button>':''}<p id="characterBoardHint" class="hint" role="status">${onBoard?'Muestra su casilla, sin mover la ficha.':'Esta ficha no está en el tablero actual. Puedes consultar sus datos aquí.'}</p>`;
 const source=prepared?`<details id="npcSheetSource"><summary>Origen y límites de esta ficha</summary>${npcProvenance(c)}<p>${esc(c.skills||'')}</p><p>${esc(c.equipment||'')}</p><p>${esc(c.feats||'')}</p></details>`:`<details><summary>Desglose calculado</summary>${creationSummary(c,d)}<p>${esc(c.feats)}</p><p>${esc(c.equipment)}</p><p>${esc(c.resources)} · ${esc(c.load)}</p><p>${esc(c.notes)}</p></details>`;
 modal(`<div class="eyebrow">${prepared?'PNJ DE LA AVENTURA':'TU PERSONAJE'}</div><h2>${esc(c.name)}</h2><p>${prepared?`${esc(c.race)} · ${esc(c.class)} ${esc(c.level)} · Director de la aventura`:'Humano · Guerrero 1'} · ${c.hp} / ${c.maxHp} PG</p>${boardLink}${prepared&&c.npcCreation.manualOverride?'<p class="notice">Esta ficha incluye una corrección manual. Sus valores actuales no se presentan como reproducción automática de la plantilla.</p>':''}${sheetChecks(c)}<div class="creator-stats"><div><small>Clase de armadura (CA)</small><strong>${c.ac}</strong></div><div><small>Ataque</small><strong>${c.attack>=0?'+':''}${c.attack}</strong></div><div><small>Daño</small><strong>${esc(c.damage)}</strong></div><div><small>Velocidad</small><strong>${c.speed*5} pies</strong></div></div>${source}<p class="hint">${prepared?'Ficha preparada por la aventura. Consulta su origen y las capacidades que todavía no cubre.':'Ficha calculada por el creador. La subida de nivel y el cambio automático de equipo aún están pendientes.'}</p>${afterCreation?`<p>${canBegin?'Tu personaje está listo. Ahora puedes elegir dónde comienza su aventura.':'Tu personaje está listo. Puedes volver a la mesa para continuar.'}</p><button type="button" class="primary" id="creatorContinue">${canBegin?'Elegir aventura':'Volver a la mesa'}</button>`:''}<details id="characterAdvanced"><summary>Corregir la ficha manualmente</summary><p id="advancedEditHint" class="hint">${esc(editReason)}</p><button id="advancedCharacterEdit" aria-describedby="advancedEditHint">Edición manual avanzada</button></details>`);
 const boardButton=$('#showCharacterOnBoard'),boardHint=$('#characterBoardHint'),sheetView=$('#modal .sheet-checks');
 if(boardButton)boardButton.onclick=()=>{
  if(!boardButton.isConnected||!$('#modal').open||!$('#modalContent').contains(boardButton))return;
  try{
   if(token!==boardScope.access||snapshot.id!==boardScope.campaign||snapshot.me.id!==boardScope.player)throw Error('La partida ha cambiado. Cierra esta hoja y vuelve a abrir la ficha que quieras consultar.');
   const target=boardCharacters(snapshot.state).find(character=>character.id===cid);if(!target)throw Error('La ficha ya no está en este tablero. Revisa su ubicación en el diario.');
   if(['wall','difficult','clear'].includes($('#tool').value)){$('#tool').value='move';path=[];ruler=[]}
   renderBoard();const cell=$$('#grid .cell').find(element=>element.dataset.tokenId===target.id);if(!cell)throw Error('No se encuentra su casilla en el tablero. Revisa la ficha antes de continuar.');
   $('#modal').close();chooseTab('board');rememberGridFocus(cell);cell.classList.add('located-token');cell.addEventListener('blur',()=>cell.classList.remove('located-token'),{once:true});cell.focus();
  }catch(error){boardHint.textContent=error.message;toast(error.message)}
 };
 if($('#creatorContinue'))$('#creatorContinue').onclick=()=>{if(!checkCharacterView(sheetView))return;$('#modal').close();chooseTab('story');if(canBegin)$('#beginAdventure')?.click()};
 $('#advancedCharacterEdit').disabled=!mayEdit||snapshot.state.board.active;
 $('#advancedCharacterEdit').onclick=()=>{if(!checkCharacterView(sheetView))return;if(confirm(prepared?'Editar manualmente registrará una corrección excepcional de la plantilla. ¿Continuar?':'Editar manualmente deja esta ficha fuera del cálculo automático. ¿Continuar?'))manualCharacterForm(cid)};
}
function creationSummary(c,d){
 return `<p>PG: ${d.hpClass} de clase ${d.hpCon>=0?'+':''}${d.hpCon} Constitución +${d.hpFavored} clase predilecta +${d.hpFeat} dotes = ${c.maxHp}.</p><p>CA: 10 +${d.armor} armadura +${d.shield} escudo ${d.dexAc>=0?'+':''}${d.dexAc} Destreza = ${c.ac}. CA desprevenido ${c.meleeProfile.flatAc}; toque ${d.touchAc}.</p><p>Salvaciones: Fortaleza ${c.saves[0]>=0?'+':''}${c.saves[0]}, Reflejos ${c.saves[1]>=0?'+':''}${c.saves[1]}, Voluntad ${c.saves[2]>=0?'+':''}${c.saves[2]}. Iniciativa ${c.initiative>=0?'+':''}${c.initiative}.</p><p>Penalizador de armadura/carga: −${d.penalty}. Peso ${(d.weight/100).toFixed(2)} libras; carga ${['ligera','media','pesada'][d.load]}.</p><details><summary>Habilidades y modificadores</summary>${d.skills.map(v=>`<p>${esc(v.name)}: ${v.ability} característica +${v.rank} rango +${v.class} clase −${v.penalty} armadura/carga = <strong>${v.total}</strong></p>`).join('')}</details>`;
}
async function startCharacterCreator(){
 if(snapshot.state.board.active){toast('Finaliza el combate antes de crear un personaje');return}
 const generation=++creatorGeneration,access=token,campaign=snapshot.id,player=snapshot.me.id;
 const sameContext=()=>generation===creatorGeneration&&token===access&&snapshot?.id===campaign&&snapshot?.me.id===player;
 const current=element=>sameContext()&&element?.isConnected&&$('#modal').open&&$('#modalContent').contains(element);
 modal('<h2>Prepara tu personaje</h2><p id="creatorLoading" role="status">Cargando las opciones del creador… Puedes cerrar esta ventana y volver después.</p>');
 const loading=$('#creatorLoading');let catalog;
 try{catalog=await getCreationCatalog()}catch(error){
  if(current(loading)){modal('<h2>Prepara tu personaje</h2><p role="status">No se han podido cargar las opciones. Tu partida sigue intacta.</p><button id="creatorRetry" class="primary">Volver a intentarlo</button>');$('#creatorRetry').onclick=run(()=>startCharacterCreator())}
  return;
 }
 if(!current(loading))return;
 if(snapshot.state.board.active){$('#modal').close();toast('Finaliza el combate antes de crear un personaje');return}
 const storageKey='cronicas-creator:'+snapshot.id+':'+snapshot.me.id;
 const makePreset=id=>({race:'human',class:'fighter',level:1,name:'',favored:'hp',...structuredClone(catalog.presets[id]),feats:['focus','initiative','toughness'],skills:['climb','intimidate','perception'],languages:[]});
 let choices=makePreset('guardian'),enemy=false,step=0,submitting=false;
 try{const draft=JSON.parse(sessionStorage.getItem(storageKey)||'null');if(draft?.version===1){choices=draft.choices;enemy=!!draft.enemy&&snapshot.me.host}}catch{}
 function saveDraft(){try{sessionStorage.setItem(storageKey,JSON.stringify({version:1,choices,enemy}))}catch{}}
 function preview(){
  const area=$('#creatorPreview'),notice=$('#creatorErrors');let result;
  try{
   result=CreationRules.calculate(catalog,choices);const c=result.data,d=result.details;
   area.innerHTML=`<div class="creator-stats"><div><small>Puntos de golpe (PG)</small><strong>${c.maxHp}</strong></div><div><small>Clase de armadura (CA)</small><strong>${c.ac}</strong></div><div><small>Ataque</small><strong>+${c.attack}</strong></div><div><small>Daño</small><strong>${esc(c.damage)}</strong></div></div><p>${c.speed*5} pies · ${d.coins[0]} po, ${d.coins[1]} pp, ${d.coins[2]} pc restantes</p>${step===3?'<details class="creator-calculation"><summary>Ver cómo se calcula la ficha</summary>'+creationSummary(c,d)+'</details>':''}`;
   notice.textContent=result.errors.join('. ');$('#creatorFinish').disabled=!!result.errors.length||!choices.name.trim();if($('#creatorReview'))$('#creatorReview').disabled=!!result.errors.length;
   const points=$('#creatorPoints');if(points)points.textContent=`${d.pointCost} / 20 puntos · ${20-d.pointCost} disponibles`;
   const ranks=$('#creatorRanks');if(ranks)ranks.textContent=`${choices.skills.length} / ${d.skillPoints} rangos asignados · ${choices.feats.length} / 3 dotes · ${choices.languages.length} / ${Math.max(0,d.mods[3])} idiomas adicionales`;
  }catch(e){area.textContent='';notice.textContent=e.message;$('#creatorFinish').disabled=true;if($('#creatorReview'))$('#creatorReview').disabled=true}
  saveDraft();return result;
 }
 function draw(focus='#creatorPage'){
  if(submitting||!sameContext())return;
  const matchesPreset=id=>Object.entries(makePreset(id)).every(([key,value])=>key==='name'||JSON.stringify(choices[key])===JSON.stringify(value));
  const option=(group,selected)=>Object.entries(catalog[group]).map(([id,v])=>`<option value="${id}" ${selected===id?'selected':''}>${esc(v.name)}</option>`).join('');
  const checkboxes=(group,selected,kind)=>Object.entries(catalog[group]).map(([id,v])=>`<label class="check"><input type="checkbox" data-choice-list="${kind}" value="${esc(id)}" ${selected.includes(id)?'checked':''}>${esc(v.name)}${kind==='feats'&&v.combat?' · combate':''}${kind==='skills'&&v.class?' · de clase':''}</label>`).join('');
  const pages=[
   `<label>Nombre<input id="creatorName" maxlength="80" value="${esc(choices.name)}" autocomplete="off" required></label><p>Humano · Guerrero · Nivel 1. Elige un punto de partida; podrás cambiar sus elecciones en los pasos siguientes.</p><div class="creator-presets">${Object.entries(catalog.presets).map(([id,p])=>`<button type="button" data-creator-preset="${id}" aria-pressed="${matchesPreset(id)}"><strong>${esc(p.name)}</strong><small>${matchesPreset(id)?'Elegido · ':''}${esc(p.description)}</small></button>`).join('')}</div><p class="hint">Este primer bloque cubre humanos guerreros de nivel 1, sin arquetipos. Otras razas, clases y niveles están pendientes; no se ofrecen como automatizados.</p>`,
   `<p>Compra de 20 puntos antes del +2 racial. El motor comprueba el presupuesto.</p><strong id="creatorPoints"></strong><div class="creator-abilities">${catalog.abilities.map((a,i)=>`<label>${esc(a)}<input data-creator-ability="${i}" type="number" min="7" max="18" value="${choices.abilities[i]}"></label>`).join('')}</div><label>Bonificador humano +2<select data-creator-field="bonus">${catalog.abilities.map((a,i)=>`<option value="${i}" ${choices.bonus===i?'selected':''}>${esc(a)}</option>`).join('')}</select></label><label>Beneficio de clase predilecta<select data-creator-field="favored"><option value="hp" ${choices.favored==='hp'?'selected':''}>+1 punto de golpe</option><option value="skill" ${choices.favored==='skill'?'selected':''}>+1 rango de habilidad</option></select></label><p class="hint">El perfil de combate actual requiere Fuerza final 10 o más para evitar daño con penalizador todavía no cubierto.</p>`,
   `<strong id="creatorRanks"></strong><h3>Dotes</h3><p>Elige tres distintas. Al menos una debe ser de combate para la dote adicional de guerrero.</p><div class="creator-choices">${checkboxes('feats',choices.feats,'feats')}</div><h3>Habilidades</h3><p>Asigna un rango a cada habilidad elegida. El +3 de clase y la armadura se calculan automáticamente.</p><div class="creator-choices">${checkboxes('skills',choices.skills,'skills')}</div><h3>Idiomas adicionales</h3><p>Común ya está incluido. Elige idiomas adicionales si tienes bonificador de Inteligencia.</p><div class="creator-choices">${catalog.languages.map(v=>`<label class="check"><input type="checkbox" data-choice-list="languages" value="${esc(v)}" ${choices.languages.includes(v)?'checked':''}>${esc(v)}</label>`).join('')}</div>`,
   `<div class="row"><label>Arma<select data-creator-field="weapon">${option('weapons',choices.weapon)}</select></label><label>Armadura<select data-creator-field="armor">${option('armors',choices.armor)}</select></label><label>Escudo<select data-creator-field="shield">${option('shields',choices.shield)}</select></label></div><p>175 po iniciales de media; incluye equipo de viaje y atuendo inicial. Precio, monedas, peso y carga se calculan juntos. El arma elegida queda equipada y lista para el combate básico.</p>`
  ];
  modal(`<div class="eyebrow">CREADOR DE PERSONAJES · PATHFINDER 1e</div><h2>Tu aventurero, paso a paso</h2><nav class="creator-steps" aria-label="Pasos del creador">${['Concepto','Características','Elecciones','Equipo y resumen'].map((label,i)=>`<button type="button" data-creator-step="${i}" ${step===i?'aria-current="step"':''}>${i+1}. ${label}</button>`).join('')}</nav><form id="creatorForm"><section id="creatorPage" tabindex="-1" aria-label="Paso ${step+1} de 4 · ${['Concepto','Características','Elecciones','Equipo y resumen'][step]}">${pages[step]}</section><p id="creatorErrors" role="status"></p><div id="creatorPreview" aria-live="polite" ${step===0?'hidden':''}></div><div class="toolbar"><button type="button" id="creatorBack" ${step===0?'hidden':''}>Anterior</button><button type="button" id="creatorNext" ${step===3?'hidden':''}>${step===0?'Personalizar':'Siguiente'}</button>${step===0?'<button type="button" id="creatorReview" class="primary">Revisar mi personaje</button>':''}<button class="primary" id="creatorFinish" ${step!==3?'hidden':''}>Crear personaje y jugar</button></div><details id="creatorAdvanced"><summary>Opciones avanzadas</summary>${snapshot.me.host?`<label class="check"><input id="creatorEnemy" type="checkbox" ${enemy?'checked':''}> Crear un adversario para la mesa</label>`:''}<button type="button" id="creatorManual">Crear ficha manual avanzada</button></details></form>`);
  const form=$('#creatorForm');
  form.oninput=e=>{
   if(submitting||!current(form))return;
   const el=e.target;if(el.id==='creatorName')choices.name=el.value;
   if(el.id==='creatorEnemy')enemy=el.checked;
   if(el.dataset.creatorAbility!==undefined)choices.abilities[Number(el.dataset.creatorAbility)]=el.value===''?null:Number(el.value);
   if(el.dataset.creatorField){const field=el.dataset.creatorField;choices[field]=field==='bonus'?Number(el.value):el.value;if(field==='weapon'&&catalog.weapons[el.value].hands===2){choices.shield='none';const shield=$('[data-creator-field="shield"]');if(shield)shield.value='none'}}
   if(el.dataset.choiceList){const field=el.dataset.choiceList;choices[field]=el.checked?[...choices[field],el.value]:choices[field].filter(v=>v!==el.value)}
   preview();
  };
  $$('[data-creator-step]').forEach(el=>el.onclick=()=>{step=Number(el.dataset.creatorStep);draw()});
  $$('[data-creator-preset]').forEach(el=>el.onclick=()=>{const name=choices.name;choices={...makePreset(el.dataset.creatorPreset),name};draw('[data-creator-preset='+el.dataset.creatorPreset+']')});
  $('#creatorBack').onclick=()=>{step--;draw()};$('#creatorNext').onclick=()=>{step++;draw()};
  if($('#creatorReview'))$('#creatorReview').onclick=()=>{if(!$('#creatorForm').reportValidity())return;step=3;draw()};
  $('#creatorManual').onclick=()=>manualCharacterForm();
  form.onsubmit=run(async()=>{
   if(submitting||!current(form))return;
   if(step!==3){step=step===0?3:step+1;draw();return}
   const result=preview();if(!result||result.errors.length||!choices.name.trim())throw Error('Completa las elecciones antes de crear el personaje');
   const submittedName=choices.name.trim(),submittedEnemy=enemy,priorIds=new Set(snapshot.state.characters.map(c=>c.id));
   let submittedDraft;try{submittedDraft=sessionStorage.getItem(storageKey)}catch{}
   const controls=$$('#modalContent button, #modalContent input, #modalContent select, #modalContent textarea').map(element=>({element,disabled:element.disabled}));
   submitting=true;controls.forEach(({element})=>element.disabled=true);$('#creatorErrors').textContent=`Guardando a ${submittedName}. Estará en la mesa aunque cierres esta ventana.`;
   try{
    await act('create_character',{choices,enemy});
    try{if(generation===creatorGeneration&&sessionStorage.getItem(storageKey)===submittedDraft)sessionStorage.removeItem(storageKey)}catch{}
    if(!current(form)){toast(`${submittedName}: personaje creado y disponible en la mesa`);return}
    const matches=snapshot.state.characters.filter(c=>!priorIds.has(c.id)&&c.owner===player&&c.name===submittedName&&!!c.enemy===submittedEnemy);
    if(matches.length===1){const created=matches[0];$('#boardCharacter').value=created.id;$('#speaker').value=created.id;renderBoard();$('#modal').close();characterForm(created.id,true)}
    else{$('#modal').close();toast('Personaje creado. Elige su ficha en la mesa.');return}
    toast('Personaje creado y listo para jugar');
   }finally{
    submitting=false;
    if(current(form)){controls.forEach(({element,disabled})=>element.disabled=disabled);$('#creatorErrors').textContent='Puedes revisar tus elecciones. Si hay un envío pendiente, recupéralo antes de crear otro personaje.'}
   }
  });preview();$(focus)?.focus();
 }
 draw(step===0?'#creatorName':'#creatorPage');
}
