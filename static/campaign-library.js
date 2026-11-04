/* Profile-local access index. Campaigns themselves remain in Firebase. */
(function(root,factory){const value=factory();if(typeof module==='object'&&module.exports)module.exports=value;else root.CampaignLibrary=value})(typeof window==='object'?window:globalThis,()=>{
 const KEY='cronicas-library-v1',MAX_ENTRIES=100;
 function checkedText(value,max){if(typeof value!=='string'||!value.length||value.length>max)throw Error('Dato de biblioteca inválido');return value}
 function validate(raw){
  if(!raw||raw.format!=='cronicas-access-1'||!Array.isArray(raw.entries)||raw.entries.length>MAX_ENTRIES)throw Error('Formato de accesos incompatible');
  const ids=new Set();
  return {format:'cronicas-access-1',entries:raw.entries.map(entry=>{
   if(!entry||typeof entry!=='object')throw Error('Acceso de biblioteca inválido');
   const campaign=checkedText(entry.campaign,200),player=checkedText(entry.player,200),id=campaign+':'+player;
   if(entry.id!==id||ids.has(id))throw Error('Acceso de biblioteca duplicado o inválido');ids.add(id);
   const token=checkedText(entry.token,256);if(!/^[a-zA-Z0-9_-]{32,256}$/.test(token))throw Error('Credencial de campaña inválida');
   if(!Array.isArray(entry.characters)||entry.characters.length>400)throw Error('Lista de personajes inválida');
   const characters=entry.characters.map(c=>{
    if(entry.ruleset==='cairn-1e')return {id:checkedText(c.id,200),name:checkedText(c.name,80),background:checkedText(c.background,80)};
    const item={id:checkedText(c.id,200),name:checkedText(c.name,80),race:checkedText(c.race,80),class:checkedText(c.class,80),level:c.level};
    if(!Number.isInteger(item.level)||item.level<1||item.level>100)throw Error('Nivel de personaje inválido');
    if(c.choices!==undefined){if(!c.choices||typeof c.choices!=='object'||Array.isArray(c.choices)||JSON.stringify(c.choices).length>20000)throw Error('Plantilla de personaje inválida');item.choices=JSON.parse(JSON.stringify(c.choices))}
    return item;
   });
   return {id,campaign,player,token,title:checkedText(entry.title,120),playerName:checkedText(entry.playerName,120),
    ruleset:checkedText(entry.ruleset,80),host:!!entry.host,characters};
  })};
 }
 function read(storage){const raw=storage.getItem(KEY);return raw?validate(JSON.parse(raw)):{format:'cronicas-access-1',entries:[]}}
 function write(storage,data){const value=validate(data),serialized=JSON.stringify(value);if(new TextEncoder().encode(serialized).length>750000)throw Error('La biblioteca supera su límite local de 750 KiB; sus accesos anteriores se conservan');if(storage.getItem(KEY)!==serialized)storage.setItem(KEY,serialized);return value}
 function record(storage,snapshot,token){
  const library=read(storage),entry={id:snapshot.id+':'+snapshot.me.id,campaign:snapshot.id,player:snapshot.me.id,token,
   title:snapshot.title,playerName:snapshot.me.name,ruleset:snapshot.state.ruleset||'pathfinder-1e',host:!!snapshot.me.host,
   characters:snapshot.state.characters.filter(c=>c.owner===snapshot.me.id&&!c.enemy).map(c=>snapshot.state.ruleset==='cairn-1e'?{
    id:c.id,name:c.name,background:c.background}:({
    id:c.id,name:c.name,race:c.race,class:c.class,level:c.level,
    ...(c.creation&&!c.creation.manualOverride?{choices:c.creation.choices}:{})}))};
  const previous=library.entries.findIndex(v=>v.id===entry.id);
  if(previous<0){if(library.entries.length>=MAX_ENTRIES)throw Error('La biblioteca admite hasta 100 accesos; guarda una copia antes de retirar alguno');library.entries.unshift(entry)}
  else library.entries[previous]=entry;
  return write(storage,library);
 }
 function merge(storage,raw){
  const incoming=validate(raw),current=read(storage),entries=new Map(current.entries.map(v=>[v.id,v]));
  for(const entry of incoming.entries)entries.set(entry.id,entry);
  return write(storage,{format:'cronicas-access-1',entries:[...entries.values()]});
 }
 function template(entry,character,targetRuleset){
  if(entry.ruleset!==targetRuleset||entry.ruleset!=='pathfinder-1e')throw Error('El personaje no es compatible con el sistema de esta campaña');
  if(!character.choices)throw Error('Esta ficha no tiene una plantilla de creación automática compatible');
  return JSON.parse(JSON.stringify(character.choices));
 }
 return {read,record,merge,template,validate,key:KEY};
});
