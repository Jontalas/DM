const assert=require('node:assert/strict');
const library=require('./static/campaign-library.js');
class Storage{
 constructor(){this.values=new Map();this.writes=0}
 getItem(key){return this.values.get(key)||null}
 setItem(key,value){this.values.set(key,value);this.writes++}
}
const token='a'.repeat(64),storage=new Storage();
const snapshot={id:'room-a',title:'Primera campaña',me:{id:'ana',name:'Ana',host:true},state:{
 secrets:'DO-NOT-CACHE',private:{ana:'PRIVATE-NOTE'},directorMemory:'PRIVATE-DIRECTOR',
 characters:[{id:'aria',owner:'ana',name:'Aria',race:'Humano',class:'Guerrero',level:1,hp:16,creation:{choices:{name:'Aria',level:1}}},
             {id:'guest',owner:'luis',name:'PRIVATE-OTHER-CHARACTER',race:'Humano',class:'Guerrero',level:1},
             {id:'enemy',owner:'ana',enemy:true,name:'OTHER-ENEMY',race:'Humano',class:'Guerrero',level:1}]}};
library.record(storage,snapshot,token);
const stored=storage.getItem(library.key);
for(const text of ['DO-NOT-CACHE','PRIVATE-NOTE','PRIVATE-DIRECTOR','PRIVATE-OTHER-CHARACTER','OTHER-ENEMY'])assert.ok(!stored.includes(text));
assert.equal(library.read(storage).entries[0].characters.length,1);
const count=storage.writes;library.record(storage,snapshot,token);assert.equal(storage.writes,count);
snapshot.state.characters[0].hp=7;library.record(storage,snapshot,token);assert.equal(storage.writes,count);
const source=library.read(storage).entries[0],copy=library.template(source,source.characters[0],'pathfinder-1e');
copy.name='A different copy';assert.equal(library.read(storage).entries[0].characters[0].choices.name,'Aria');
assert.throws(()=>library.template(source,source.characters[0],'other-system'));
assert.throws(()=>library.template(source,{name:'Manual'},'pathfinder-1e'));
const second=JSON.parse(JSON.stringify(snapshot));second.me={id:'luis',name:'Luis',host:false};
library.record(storage,second,'b'.repeat(64));assert.equal(library.read(storage).entries.length,2);
assert.equal(library.read(storage).entries.find(entry=>entry.player==='luis').characters[0].name,'PRIVATE-OTHER-CHARACTER');
const backup=JSON.parse(storage.getItem(library.key)),restored=new Storage();library.merge(restored,backup);
assert.deepEqual(library.read(restored),backup);
const before=restored.getItem(library.key);
assert.throws(()=>library.merge(restored,{format:'invalid',entries:[]}));assert.equal(restored.getItem(library.key),before);
const broken=new Storage();broken.setItem(library.key,'broken-json');assert.throws(()=>library.read(broken));assert.equal(broken.getItem(library.key),'broken-json');
const quota={getItem:key=>storage.getItem(key),setItem:()=>{throw Error('QuotaExceeded')}};
const changed=JSON.parse(JSON.stringify(snapshot));changed.title='Changed';assert.throws(()=>library.record(quota,changed,token));
assert.equal(library.read(storage).entries[0].title,'Primera campaña');
console.log('OK: profile access persistence, owner-only characters, no cached secrets, no redundant writes, backup validation, corruption preservation and compatible initial templates.');
const cairn={id:'cairn-room',title:'Cairn',me:{id:'ana',name:'Ana',host:true},state:{ruleset:'cairn-1e',characters:[
 {id:'woodlander',name:'Agune Abernathy',owner:'ana',background:'Alchemist',creation:{draft:{SECRET:'not-cached'}}}]}};
library.record(storage,cairn,'c'.repeat(64));
const cairnEntry=library.read(storage).entries.find(e=>e.ruleset==='cairn-1e');
assert.deepEqual(cairnEntry.characters,[{id:'woodlander',name:'Agune Abernathy',background:'Alchemist'}]);
assert.ok(!storage.getItem(library.key).includes('not-cached'));
assert.throws(()=>library.template(cairnEntry,cairnEntry.characters[0],'pathfinder-1e'));
const generic={id:'generic-room',title:'Imported rules',me:{id:'ana',name:'Ana',host:true},state:{ruleset:'rule-pack',package:{document:{privateSource:'NOT-CACHED'}},characters:[
 {id:'traveler',name:'Lúa',owner:'ana',sheet:{fields:{energy:3}}}]}};
library.record(storage,generic,'d'.repeat(64));
const genericEntry=library.read(storage).entries.find(e=>e.ruleset==='rule-pack');
assert.deepEqual(genericEntry.characters,[{id:'traveler',name:'Lúa'}]);
assert.ok(!storage.getItem(library.key).includes('NOT-CACHED'));assert.ok(!('level' in genericEntry.characters[0]));
const genericWrites=storage.writes;library.record(storage,generic,'d'.repeat(64));assert.equal(storage.writes,genericWrites);
assert.throws(()=>library.template(genericEntry,genericEntry.characters[0],'rule-pack'));
