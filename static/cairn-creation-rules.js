/* Local preview of Cairn SRD v1.0, Yochai Gal, CC BY-SA 4.0.
 * https://cairnrpg.com/first-edition/cairn-srd/
 * Changes: deterministic client preview; server always rebuilds authoritative state.
 */
(function(root,factory){const value=factory();if(typeof module==='object'&&module.exports)module.exports=value;else root.CairnCreation=value})(typeof window==='object'?window:globalThis,()=>{
 function groups(draft,tables){
  const rows=['armor','helmets--shields','weapons','expeditionary-gear','tools','trinkets'].map(id=>({id,table:id,raw:draft.gear[id]}));
  if(draft.bonus)rows.push({id:'bonus',...draft.bonus});
  return rows.map(row=>{const label=tables[row.table][row.raw-1];return {...row,chooseOne:row.table==='weapons',
   options:row.table==='spellbooks-d100'?['Spellbook: '+label]:label==='None'?[]:row.table==='weapons'?label.split(', '):row.table==='helmets--shields'?label.split(' & '):[label]}});
 }
 function equipment(draft,choices,tables){
  const inventory=[{id:'rations',item:'Rations (three days)',state:'carried'},{id:'torch',item:'Torch',state:'carried'}],pending=[];
  if(!draft.bonus)pending.push('Elige la tabla del objeto adicional.');
  for(const group of groups(draft,tables)){
   let options=group.options;
   if(group.chooseOne){const name=choices.weapons?.[group.id];if(!name){pending.push('Elige un arma de la fila obtenida.');continue}if(!options.includes(name))throw Error('Arma fuera del resultado original.');options=[name]}
   options.forEach((item,i)=>inventory.push({id:group.id+':'+i,item,state:'carried'}));
  }
  inventory.forEach(entry=>entry.state=choices.disposition?.[entry.id]||'carried');
  return {inventory,pending};
 }
 function calculate(draft,choices,resources){
  const tables=resources.tables.tables,abilities=Object.fromEntries(['STR','DEX','WIL'].map(key=>[key,draft.core[key].reduce((a,b)=>a+b,0)]));
  if(choices.swap?.length){const [a,b]=choices.swap;if(choices.swap.length!==2||a===b||!(a in abilities)||!(b in abilities))throw Error('Intercambio inválido.');[abilities[a],abilities[b]]=[abilities[b],abilities[a]]}
  const identity={...draft.identity,...choices.identity},name=tables[draft.nameTable][identity.name-1]+' '+tables.surnames[identity.surname-1],background=tables.background[identity.background-1];
  const {inventory,pending}=equipment(draft,choices,tables);let slots=0,armor=0,hands=0;const equipped=[];
  for(const entry of inventory){
   const item=resources.items[entry.item];if(!item)throw Error('Equipo todavía no verificado: '+entry.item);
   if(!['carried','equipped','stored'].includes(entry.state))throw Error('Estado de equipo inválido.');
   if(entry.state==='stored')continue;
   if(item.requiresAdjudication)throw Error('El transporte de este objeto sigue pendiente; decide si guardarlo fuera.');
   slots+=item.slots;
   if(entry.state==='equipped'){
    if(item.requiresHandRuling||!item.equip)throw Error('Ese uso del equipo todavía requiere resolución contextual.');
    armor+=item.armor;hands+=item.hands;equipped.push(entry.item);
   }
  }
  if(slots>10)throw Error('El equipo ocupa '+slots+' de diez espacios. Elige qué guardar fuera.');
  if(hands>2)throw Error('El equipo requiere más de dos manos.');
  if(['Helmet','Shield'].some(name=>equipped.filter(v=>v===name).length>1))throw Error('Protecciones repetidas: requieren resolución contextual.');
  return {abilities,name,background,inventory,inventorySlots:slots,armor:Math.min(3,armor),hitProtection:slots===10?0:draft.core.HP[0],
   age:10+draft.core.age.reduce((a,b)=>a+b,0),gold:draft.core.gold.reduce((a,b)=>a+b,0),pending};
 }
 return {groups,equipment,calculate};
});
