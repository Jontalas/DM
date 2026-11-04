/* Private preparation, separate from installation and play. */
window.RulePackAuthoringUI=(()=>{
 const drafts=new Map();
 const key=()=>snapshot.id+':'+snapshot.me.id;
 function openForm(){
  const current=key(),saved=drafts.get(current)||{};
  modal(`<div class="eyebrow">PREPARAR REGLAS DESDE UN DOCUMENTO</div><h2>Un bloque de reglas verificable</h2><p>Aporta los fragmentos necesarios para una mecánica concreta. El importador de PDF y los manuales completos siguen pendientes.</p><form id="packPrepare"><label>Título del documento<input name="title" maxlength="200" required></label><label>Edición<input name="edition" maxlength="200" required></label><label>Leer texto desde un archivo, opcional<input id="packSourceFile" type="file" accept=".txt,.md,text/plain,text/markdown"></label><label>Página o número de fragmento<input name="page" type="number" min="1" max="100000" value="1" step="1" required></label><label>Fragmento de reglas<textarea name="text" maxlength="24000" rows="7" required></textarea></label><label>Qué mecánica debe preparar<textarea name="scope" maxlength="1200" rows="2" required placeholder="Por ejemplo: características iniciales y pruebas de salvación"></textarea></label><label>Autoría y atribución<input name="attribution" maxlength="2000" required></label><label>Ámbito de uso aportado<select name="permission"><option value="private-use">Uso privado · no declara permiso de redistribución</option><option value="redistributable">Dispongo de permiso para redistribuir</option></select></label><details><summary>Identidad del paquete y licencia declarada</summary><label>Identificador, opcional<input name="identifier" pattern="[a-z][a-z0-9_-]{0,63}" maxlength="64" placeholder="Se genera desde el título"></label><label>Versión<input name="version" value="0.1.0" pattern="[0-9]+[.][0-9]+[.][0-9]+" required></label><label>Licencia o referencia de uso<input name="license" value="private-reference" maxlength="200" required></label></details><p class="hint">Se enviará este fragmento a Claude Haiku en una llamada, con salida limitada. No se envía el resto de la campaña. Se conserva la última preparación en privado y no se instala automáticamente. No se reintenta una inferencia fallida.</p><button class="primary" ${model.aiConfigured?'':'disabled'}>Preparar con IA · una llamada</button></form>`);
  const form=$('#packPrepare');for(const [name,value] of Object.entries(saved))if(form.elements[name])form.elements[name].value=value;
  function remember(){const value=values(form);delete value[''];drafts.set(current,value);}
  form.oninput=remember;form.onchange=remember;
  $('#packSourceFile').onchange=run(async e=>{
   const file=e.target.files[0];if(!file)return;if(file.size>96000)throw Error('Selecciona un fragmento de texto de hasta 24.000 caracteres.');
   const text=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());
   if(text.length>24000||text.includes('\0'))throw Error('El texto supera el límite o no es un documento de texto válido.');
   form.elements.text.value=text;remember();
  });
  form.onsubmit=run(async()=>{
   if(key()!==current||$('#app').hidden)throw Error('Abre la preparación desde su campaña.');
   remember();const v=values(form);
   const slug=v.title.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'');
   const request={identity:{id:v.identifier||('rules-'+slug).slice(0,64).replace(/-+$/,''),name:v.title,edition:v.edition,version:v.version},
    license:{id:v.license,attribution:v.attribution},permission:v.permission,scope:v.scope,
    document:{title:v.title,edition:v.edition,pages:[{page:Number(v.page),text:v.text}]}};
   await act('prepare_rule_pack',{request});drafts.delete(current);$('#modal').close();
  });
 }
 function openReport(){
  const record=snapshot.state.authoring;if(!record)return;
  const report=record.report,candidate=report.candidate;
  modal(`<div class="eyebrow">PREPARACIÓN PRIVADA DEL ANFITRIÓN</div><h2>${candidate?'Propuesta de reglas':'Reglas pendientes de resolver'}</h2><p class="notice">La IA propone una interpretación. Los ejemplos comprueban coherencia interna; no certifican correspondencia con el manual.</p>${report.issues.map(i=>`<p><strong>${esc({ambiguity:'Ambigüedad',unsupported:'Operación no disponible',coverage:'Cobertura'}[i.kind])}</strong> · ${esc(i.message)}</p>`).join('')}${candidate?`<p>${esc(candidate.name)} · ${report.checks.length} ejemplos comprobados sin azar.</p><ul>${report.checks.map(c=>`<li>${esc(c.name)}</li>`).join('')}</ul><button id="packReviewPrepared" class="primary">Revisar paquete antes de instalar</button>`:'<p>No se ha creado un paquete ejecutable. Aporta las reglas que faltan o espera a que el motor cubra la operación; no se aplicarán equivalencias de otro juego.</p>'}<details><summary>Fragmentos originales y alcance aportados</summary><p>${esc(record.request.scope)}</p>${record.request.document.pages.map(p=>`<h4>Página/fragmento ${p.page}</h4><pre class="pack-source">${esc(p.text)}</pre>`).join('')}</details>${report.usage?`<small>Preparación guardada: ${report.usage.inputTokens} tokens de entrada y ${report.usage.outputTokens} de salida. Consultar este informe no llama a IA.</small>`:''}`);
  if($('#packReviewPrepared'))$('#packReviewPrepared').onclick=()=>{
   const view={...candidate,fields:Object.keys(candidate.fields).length,actions:Object.keys(candidate.actions).length,tables:Object.keys(candidate.tables).length};
   RulePackUI.review(candidate,view,record.sha256);
  };
 }
 function render(root){
  if(!snapshot.me.host)return;
  const record=snapshot.state.authoring;
  if(snapshot.state.characters.length&&!record)return;
  root.querySelector('.pack-columns > section').insertAdjacentHTML('afterbegin',`<section class="card"><h3>Preparar desde reglas escritas</h3><p>Convierte un fragmento de texto en una propuesta revisable. No admite todavía un manual completo ni PDF.</p>${!snapshot.state.characters.length?`<button id="packPrepareOpen" ${model.aiConfigured?'':'disabled'}>Aportar reglas y preparar con IA</button>${!model.aiConfigured?'<small>Anthropic no está configurado. Puedes seguir importando un paquete JSON ya preparado.</small>':''}`:''}${record?'<button id="packPreparationReport">Consultar preparación guardada</button>':''}</section>`);
  if($('#packPrepareOpen'))$('#packPrepareOpen').onclick=openForm;
  if($('#packPreparationReport'))$('#packPreparationReport').onclick=openReport;
 }
 return {render};
})();
