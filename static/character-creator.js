/* Step-by-step local creation; exactly one campaign action when confirmed. */
let creationCatalog;
document.addEventListener('click',e=>{if(e.target.closest('[data-create-hero]'))characterForm()});
async function getCreationCatalog(){
 if(!creationCatalog)creationCatalog=fetch('/creation-catalog.json?v=1').then(r=>{if(!r.ok)throw Error('No se pudo cargar el creador');return r.json()}).catch(e=>{creationCatalog=null;throw e});
 return creationCatalog;
}
function characterForm(cid){
 if(!cid){run(()=>startCharacterCreator())();return}
 const c=snapshot.state.characters.find(v=>v.id===cid);
 if(!c?.creation||c.creation.manualOverride){manualCharacterForm(cid);return}
 const d=c.creation.details;
 modal(`<div class="eyebrow">PERSONAJE LISTO PARA JUGAR</div><h2>${esc(c.name)}</h2><p>Humano · Guerrero 1 · ${c.hp} / ${c.maxHp} PG</p>${sheetChecks(c)}<div class="creator-stats"><div><small>CA</small><strong>${c.ac}</strong></div><div><small>Ataque</small><strong>${c.attack>=0?'+':''}${c.attack}</strong></div><div><small>Daño</small><strong>${esc(c.damage)}</strong></div><div><small>Velocidad</small><strong>${c.speed*5} pies</strong></div></div><details><summary>Desglose calculado</summary>${creationSummary(c,d)}<p>${esc(c.feats)}</p><p>${esc(c.equipment)}</p><p>${esc(c.resources)} · ${esc(c.load)}</p><p>${esc(c.notes)}</p></details><p class="hint">Ficha calculada por el creador. La subida de nivel y el cambio automático de equipo aún están pendientes.</p><button id="advancedCharacterEdit">Edición manual avanzada</button>`);
 $('#advancedCharacterEdit').disabled=(!snapshot.me.host&&c.owner!==snapshot.me.id)||snapshot.state.board.active;
 $('#advancedCharacterEdit').onclick=()=>{if(confirm('Editar manualmente deja esta ficha fuera del cálculo automático. ¿Continuar?'))manualCharacterForm(cid)};
}
function creationSummary(c,d){
 return `<p>PG: ${d.hpClass} de clase ${d.hpCon>=0?'+':''}${d.hpCon} Constitución +${d.hpFavored} clase predilecta +${d.hpFeat} dotes = ${c.maxHp}.</p><p>CA: 10 +${d.armor} armadura +${d.shield} escudo ${d.dexAc>=0?'+':''}${d.dexAc} Destreza = ${c.ac}. CA desprevenido ${c.meleeProfile.flatAc}; toque ${d.touchAc}.</p><p>Salvaciones: Fortaleza ${c.saves[0]>=0?'+':''}${c.saves[0]}, Reflejos ${c.saves[1]>=0?'+':''}${c.saves[1]}, Voluntad ${c.saves[2]>=0?'+':''}${c.saves[2]}. Iniciativa ${c.initiative>=0?'+':''}${c.initiative}.</p><p>Penalizador de armadura/carga: −${d.penalty}. Peso ${(d.weight/100).toFixed(2)} libras; carga ${['ligera','media','pesada'][d.load]}.</p><details><summary>Habilidades y modificadores</summary>${d.skills.map(v=>`<p>${esc(v.name)}: ${v.ability} característica +${v.rank} rango +${v.class} clase −${v.penalty} armadura/carga = <strong>${v.total}</strong></p>`).join('')}</details>`;
}
async function startCharacterCreator(){
 if(snapshot.state.board.active){toast('Finaliza el combate antes de crear un personaje');return}
 const catalog=await getCreationCatalog();if(!snapshot)return;
 const storageKey='cronicas-creator:'+snapshot.id+':'+snapshot.me.id;
 const makePreset=id=>({race:'human',class:'fighter',level:1,name:'',favored:'hp',...structuredClone(catalog.presets[id]),feats:['focus','initiative','toughness'],skills:['climb','intimidate','perception'],languages:[]});
 let choices=makePreset('guardian'),enemy=false,step=0;
 try{const draft=JSON.parse(sessionStorage.getItem(storageKey)||'null');if(draft?.version===1){choices=draft.choices;enemy=!!draft.enemy&&snapshot.me.host}}catch{}
 function saveDraft(){try{sessionStorage.setItem(storageKey,JSON.stringify({version:1,choices,enemy}))}catch{}}
 function preview(){
  const area=$('#creatorPreview'),notice=$('#creatorErrors');let result;
  try{
   result=CreationRules.calculate(catalog,choices);const c=result.data,d=result.details;
   area.innerHTML=`<div class="creator-stats"><div><small>PG</small><strong>${c.maxHp}</strong></div><div><small>CA</small><strong>${c.ac}</strong></div><div><small>Ataque</small><strong>+${c.attack}</strong></div><div><small>Daño</small><strong>${esc(c.damage)}</strong></div></div><p>${c.speed*5} pies · ${d.coins[0]} po, ${d.coins[1]} pp, ${d.coins[2]} pc restantes</p>${step===3?creationSummary(c,d):''}`;
   notice.textContent=result.errors.join('. ');$('#creatorFinish').disabled=!!result.errors.length||!choices.name.trim();
   const points=$('#creatorPoints');if(points)points.textContent=`${d.pointCost} / 20 puntos · ${20-d.pointCost} disponibles`;
   const ranks=$('#creatorRanks');if(ranks)ranks.textContent=`${choices.skills.length} / ${d.skillPoints} rangos asignados · ${choices.feats.length} / 3 dotes · ${choices.languages.length} / ${Math.max(0,d.mods[3])} idiomas adicionales`;
  }catch(e){area.textContent='';notice.textContent=e.message;$('#creatorFinish').disabled=true}
  saveDraft();return result;
 }
 function draw(){
  const option=(group,selected)=>Object.entries(catalog[group]).map(([id,v])=>`<option value="${id}" ${selected===id?'selected':''}>${esc(v.name)}</option>`).join('');
  const checkboxes=(group,selected,kind)=>Object.entries(catalog[group]).map(([id,v])=>`<label class="check"><input type="checkbox" data-choice-list="${kind}" value="${esc(id)}" ${selected.includes(id)?'checked':''}>${esc(v.name)}${kind==='feats'&&v.combat?' · combate':''}${kind==='skills'&&v.class?' · de clase':''}</label>`).join('');
  const pages=[
   `<label>Nombre<input id="creatorName" maxlength="80" value="${esc(choices.name)}" autocomplete="off" required></label><p>Humano · Guerrero · Nivel 1. Elige un punto de partida; podrás cambiar sus elecciones en los pasos siguientes.</p><div class="creator-presets">${Object.entries(catalog.presets).map(([id,p])=>`<button type="button" data-creator-preset="${id}"><strong>${esc(p.name)}</strong><small>${esc(p.description)}</small></button>`).join('')}</div>${snapshot.me.host?`<label class="check"><input id="creatorEnemy" type="checkbox" ${enemy?'checked':''}> Adversario controlado por el maestro</label>`:''}<p class="hint">Este primer bloque cubre humanos guerreros de nivel 1, sin arquetipos. Otras razas, clases y niveles están pendientes; no se ofrecen como automatizados.</p>`,
   `<p>Compra de 20 puntos antes del +2 racial. El motor comprueba el presupuesto.</p><strong id="creatorPoints"></strong><div class="creator-abilities">${catalog.abilities.map((a,i)=>`<label>${esc(a)}<input data-creator-ability="${i}" type="number" min="7" max="18" value="${choices.abilities[i]}"></label>`).join('')}</div><label>Bonificador humano +2<select data-creator-field="bonus">${catalog.abilities.map((a,i)=>`<option value="${i}" ${choices.bonus===i?'selected':''}>${esc(a)}</option>`).join('')}</select></label><label>Beneficio de clase predilecta<select data-creator-field="favored"><option value="hp" ${choices.favored==='hp'?'selected':''}>+1 punto de golpe</option><option value="skill" ${choices.favored==='skill'?'selected':''}>+1 rango de habilidad</option></select></label><p class="hint">El perfil de combate actual requiere Fuerza final 10 o más para evitar daño con penalizador todavía no cubierto.</p>`,
   `<strong id="creatorRanks"></strong><h3>Dotes</h3><p>Elige tres distintas. Al menos una debe ser de combate para la dote adicional de guerrero.</p><div class="creator-choices">${checkboxes('feats',choices.feats,'feats')}</div><h3>Habilidades</h3><p>Asigna un rango a cada habilidad elegida. El +3 de clase y la armadura se calculan automáticamente.</p><div class="creator-choices">${checkboxes('skills',choices.skills,'skills')}</div><h3>Idiomas adicionales</h3><p>Común ya está incluido. Elige idiomas adicionales si tienes bonificador de Inteligencia.</p><div class="creator-choices">${catalog.languages.map(v=>`<label class="check"><input type="checkbox" data-choice-list="languages" value="${esc(v)}" ${choices.languages.includes(v)?'checked':''}>${esc(v)}</label>`).join('')}</div>`,
   `<div class="row"><label>Arma<select data-creator-field="weapon">${option('weapons',choices.weapon)}</select></label><label>Armadura<select data-creator-field="armor">${option('armors',choices.armor)}</select></label><label>Escudo<select data-creator-field="shield">${option('shields',choices.shield)}</select></label></div><p>175 po iniciales de media; incluye equipo de viaje y atuendo inicial. Precio, monedas, peso y carga se calculan juntos. El arma elegida queda equipada y lista para el combate básico.</p>`
  ];
  modal(`<div class="eyebrow">CREADOR DE PERSONAJES · PATHFINDER 1e</div><h2>Tu aventurero, paso a paso</h2><nav class="creator-steps" aria-label="Pasos del creador">${['Concepto','Características','Elecciones','Equipo y resumen'].map((label,i)=>`<button type="button" data-creator-step="${i}" ${step===i?'aria-current="step"':''}>${i+1}. ${label}</button>`).join('')}</nav><form id="creatorForm"><section>${pages[step]}</section><p id="creatorErrors" role="status"></p><div id="creatorPreview" aria-live="polite"></div><div class="toolbar"><button type="button" id="creatorBack" ${step===0?'disabled':''}>Anterior</button><button type="button" id="creatorNext" ${step===3?'hidden':''}>Siguiente</button><button class="primary" id="creatorFinish" ${step!==3?'hidden':''}>Crear personaje y jugar</button></div></form><details><summary>Opciones avanzadas</summary><button id="creatorManual">Crear ficha manual avanzada</button></details>`);
  $('#creatorForm').oninput=e=>{
   const el=e.target;if(el.id==='creatorName')choices.name=el.value;
   if(el.id==='creatorEnemy')enemy=el.checked;
   if(el.dataset.creatorAbility!==undefined)choices.abilities[Number(el.dataset.creatorAbility)]=el.value===''?null:Number(el.value);
   if(el.dataset.creatorField){const field=el.dataset.creatorField;choices[field]=field==='bonus'?Number(el.value):el.value;if(field==='weapon'&&catalog.weapons[el.value].hands===2){choices.shield='none';const shield=$('[data-creator-field="shield"]');if(shield)shield.value='none'}}
   if(el.dataset.choiceList){const field=el.dataset.choiceList;choices[field]=el.checked?[...choices[field],el.value]:choices[field].filter(v=>v!==el.value)}
   preview();
  };
  $$('[data-creator-step]').forEach(el=>el.onclick=()=>{step=Number(el.dataset.creatorStep);draw()});
  $$('[data-creator-preset]').forEach(el=>el.onclick=()=>{const name=choices.name;choices={...makePreset(el.dataset.creatorPreset),name};draw()});
  $('#creatorBack').onclick=()=>{step--;draw()};$('#creatorNext').onclick=()=>{step++;draw()};
  $('#creatorManual').onclick=()=>manualCharacterForm();
  $('#creatorForm').onsubmit=run(async()=>{
   if(step!==3){step++;draw();return}
   const result=preview();if(!result||result.errors.length||!choices.name.trim())throw Error('Completa las elecciones antes de crear el personaje');
   await act('create_character',{choices,enemy});try{sessionStorage.removeItem(storageKey)}catch{}
   const created=snapshot.state.characters.at(-1);$('#boardCharacter').value=created.id;$('#speaker').value=created.id;renderBoard();$('#modal').close();characterForm(created.id);toast('Personaje creado y listo para jugar');
  });preview();
 }
 draw();
}
