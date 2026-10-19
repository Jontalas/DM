/* Pure local preview. The Python engine validates and recalculates on commit. */
(function(root){
function calculate(catalog,c){
 const base=c.abilities;if(!Array.isArray(base)||base.length!==6||base.some(v=>!Number.isInteger(v)||v<7||v>18))throw Error('Características base entre 7 y 18');
 if(!Number.isInteger(c.bonus)||c.bonus<0||c.bonus>5)throw Error('Elige la característica racial');
 const attrs=[...base];attrs[c.bonus]+=2;const mods=attrs.map(v=>Math.floor((v-10)/2));
 if(attrs[0]<10)throw Error('Este bloque requiere Fuerza 10 o más para el perfil de combate actual');
 const pointCost=base.reduce((s,v)=>s+catalog.costs[v],0),weapon=catalog.weapons[c.weapon],armor=catalog.armors[c.armor],shield=catalog.shields[c.shield];
 if(!weapon||!armor||!shield)throw Error('Elige el equipo');
 if(weapon.hands===2&&c.shield!=='none')throw Error('El mandoble necesita ambas manos: elige sin escudo');
 const feats=c.feats||[],ranks=c.skills||[],languages=c.languages||[];
 const inventory=[weapon,armor,shield,catalog.kit,catalog.outfit],spentCp=inventory.reduce((s,v)=>s+v.price,0),remaining=catalog.wealthCp-spentCp;
 if(remaining<0)throw Error('El equipo supera las 175 po iniciales');
 const gold=Math.floor(remaining/100),silver=Math.floor(remaining%100/10),copper=remaining%10;
 const weight=inventory.reduce((s,v)=>s+v.weight,0)*100+(gold+silver+copper)*2;
 const load=catalog.loads[attrs[0]].findIndex(limit=>weight<=limit*100);if(load<0)throw Error('El equipo supera la carga máxima');
 const penalty=Math.max(armor.penalty+shield.penalty,[0,3,6][load]),dex=Math.min(mods[1],armor.maxDex,[99,3,1][load]);
 const ac=10+armor.ac+shield.ac+dex,damageBonus=weapon.hands===2?Math.floor(mods[0]*1.5):mods[0];
 const skills=Object.entries(catalog.skills).filter(([key,v])=>!v.trained||ranks.includes(key)).map(([key,v])=>{
  const rank=Number(ranks.includes(key)),classBonus=rank&&v.class?3:0,armorPenalty=v.armor?penalty:0;
  return {name:v.name,ability:mods[v.ability],rank,class:classBonus,penalty:armorPenalty,total:mods[v.ability]+rank+classBonus-armorPenalty};
 });
 const skillPoints=Math.max(1,2+mods[3])+1+Number(c.favored==='skill'),hpCon=mods[2],hpFavored=Number(c.favored==='hp'),hpFeat=feats.includes('toughness')?3:0;
 const hp=10+hpCon+hpFavored+hpFeat;
 const data={abilities:attrs,maxHp:hp,hp,ac,saves:[2+mods[2]+(feats.includes('fortitude')?2:0),mods[1]+(feats.includes('reflexes')?2:0),mods[4]+(feats.includes('will')?2:0)],
  speed:Math.min(armor.speed,load===0?6:4),initiative:mods[1]+(feats.includes('initiative')?4:0),attack:1+mods[0]+Number(feats.includes('focus')),
  damage:weapon.dice+(damageBonus?'+'+damageBonus:''),skillTotals:skills.map(v=>({name:v.name,total:v.total})),
  meleeProfile:{flatAc:ac-Math.max(0,dex),criticalMin:weapon.criticalMin,multiplier:weapon.multiplier}};
 const details={pointCost,mods,armor:armor.ac,shield:shield.ac,dexAc:dex,touchAc:10+dex,weight,load,penalty,coins:[gold,silver,copper],spentCp,skillPoints,skills,damageBonus,hpClass:10,hpCon,hpFavored,hpFeat};
 const errors=[];
 if(pointCost>catalog.budget)errors.push('Superas los 20 puntos de características');
 if(feats.length!==3||new Set(feats).size!==3||feats.some(f=>!catalog.feats[f])||!feats.some(f=>catalog.feats[f]?.combat))errors.push('Elige tres dotes distintas, al menos una de combate');
 if(ranks.length!==skillPoints||new Set(ranks).size!==ranks.length||ranks.some(k=>!catalog.skills[k]))errors.push('Asigna '+skillPoints+' rangos: un rango por habilidad');
 if(languages.length!==Math.max(0,mods[3])||new Set(languages).size!==languages.length||languages.some(v=>!catalog.languages.includes(v)))errors.push('Elige '+Math.max(0,mods[3])+' idiomas adicionales por Inteligencia');
 return {data,details,errors};
}
const api={calculate};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.CreationRules=api;
})(typeof window!=='undefined'?window:globalThis);
