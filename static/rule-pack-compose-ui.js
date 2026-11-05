/* Reviewed composition uses deterministic endpoints; never calls the model. */
window.RulePackComposeUI=(()=>{
 function openAdditional(input){
  const record=snapshot.state.package;
  if(!snapshot.me.host||snapshot.state.characters.length||!record||$('#app').hidden)throw Error('Combina bloques desde una campaña propia todavía sin fichas.');
  if(!Array.isArray(input)||!input.length||input.length>31)throw Error('Selecciona entre uno y treinta y un bloques.');
  const additional=structuredClone(input),scope=snapshot.id+':'+snapshot.me.id,base=structuredClone(record.document),baseSha=record.sha256;
  const ensure=()=>{if($('#app').hidden||scope!==snapshot.id+':'+snapshot.me.id||snapshot.state.package?.sha256!==baseSha)throw Error('La campaña o sus reglas han cambiado; revisa la composición desde su estado actual.');};
  const versions=[base.version,...additional.map(raw=>typeof raw==='string'?JSON.parse(raw)?.version:raw?.version)];
  if(versions.some(v=>typeof v!=='string'||v.length>40||!/^\d+\.\d+\.\d+$/.test(v)))throw Error('Un paquete no declara una versión válida.');
  const latest=versions.map(v=>v.split('.').map(Number)).sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2]).at(-1);latest[2]++;
  modal(`<div class="eyebrow">COMBINAR REGLAS</div><h2>Revisar los bloques antes de guardar</h2><p>${additional.length} paquetes adicionales junto a la versión ${esc(base.version)}. Esta revisión no usa IA ni modifica la campaña.</p><form id="packComposePreview"><label>Versión del resultado<input name="versionTarget" value="${esc(latest.join('.'))}" pattern="[0-9]+[.][0-9]+[.][0-9]+" required></label><button class="primary">Revisar combinación</button></form>`);
  $('#packComposePreview').onsubmit=run(async event=>{
   ensure();const versionTarget=event.target.elements.versionTarget.value;
   const result=await api('/api/rule-pack/compose',{packages:[base,...additional],version:versionTarget});ensure();
   const doc=result.document;
   modal(`<div class="eyebrow">COMBINACIÓN REVISADA</div><h2>${esc(doc.name)} · ${esc(doc.version)}</h2><p>${Object.keys(doc.fields).length} campos · ${Object.keys(doc.actions).length} acciones · ${doc.sources.length} fuentes.</p><p class="notice">Estructura compatible. Correspondencia con el manual sin verificar; se conserva la cobertura pendiente.</p><h3>Incluido según los bloques</h3><ul>${doc.coverage.implemented.map(v=>`<li>${esc(v)}</li>`).join('')}</ul><h3>Pendiente según los bloques</h3><ul>${doc.coverage.pending.map(v=>`<li>${esc(v)}</li>`).join('')}</ul><form id="packComposeInstall"><label class="check"><input type="checkbox" name="use"> Usar las definiciones aportadas, con estos límites</label><button class="primary">Guardar combinación</button></form>`);
   $('#packComposeInstall').onsubmit=run(async event=>{
    ensure();await act('compose_rule_pack',{additional,versionTarget,baseSha256:baseSha,
     expectedSha256:result.provenance.packageSha256,policy:event.target.elements.use.checked?'provided-rules':'draft'});
    $('#modal').close();
   });
  });
 }
 function render(root){
  const s=snapshot.state,record=s.package;if(!record)return;
  const canEdit=snapshot.me.host&&!s.characters.length;
  if(!canEdit&&!record.composition)return;
  const panel=document.createElement('section');panel.className='card';panel.id='packComposePanel';
  panel.innerHTML=`<h3>Bloques del reglamento</h3>${record.composition?`<details><summary>Procedencia de esta versión</summary><p>Se combinaron ${record.composition.inputs.length} paquetes. Las huellas conservan la referencia de entrada; no certifican la autenticidad histórica de una copia externa.</p>${record.composition.inputs.map(b=>`<p>${esc(b.id)} · ${esc(b.version)}<small>SHA-256 ${esc(b.sha256)}</small></p>`).join('')}</details>`:''}${canEdit?'<p>Añade paquetes del mismo juego y edición. Los conflictos se rechazan; no se sustituyen reglas ni se resuelven licencias automáticamente.</p><label>Paquetes adicionales<input id="packComposeFiles" type="file" multiple accept=".json,application/json"></label>':''}`;
  root.querySelector('#packCharacters').before(panel);
  if(!canEdit)return;
  $('#packComposeFiles').onchange=run(async e=>{
   const files=[...e.target.files];if(!files.length)return;
   if(files.length>31||files.some(f=>f.size>256000)||files.reduce((n,f)=>n+f.size,0)>1000000)throw Error('Selecciona hasta 31 paquetes de 256.000 bytes; tamaño total máximo 1 MB.');
   const scope=snapshot.id+':'+snapshot.me.id,additional=[];
   for(const file of files){
    const raw=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());additional.push(raw);
   }
   if($('#app').hidden||scope!==snapshot.id+':'+snapshot.me.id||snapshot.state.package?.sha256!==record.sha256)throw Error('La campaña ha cambiado durante la lectura de archivos.');
   openAdditional(additional);
  });
 }
 return {render,openAdditional};
})();
