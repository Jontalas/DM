/* Read-only local expansion of private preparation data already loaded. */
(function(root,factory){const value=factory();if(typeof module==='object'&&module.exports)module.exports=value;else root.RulePreparationWorkspace=value})(typeof window==='object'?window:globalThis,()=>{
 const owns=(object,key)=>Object.prototype.hasOwnProperty.call(object,key);
 function record(state,digest){
  const workspace=state.authoringWorkspace;
  if(!workspace){const legacy=state.authoring;return legacy&&(!digest||legacy.sha256===digest)?structuredClone(legacy):null;}
  const selected=digest||workspace.latest;if(!selected||!owns(workspace.blocks,selected))return null;
  const result=structuredClone(workspace.blocks[selected]);
  result.request.document.pages=result.request.document.pages.map(reference=>{
   if(!owns(workspace.sources,reference.source))throw Error('Falta un fragmento del bloque guardado; conserva la copia para revisarla.');
   const source=workspace.sources[reference.source];
   if(!owns(workspace.texts,source.sha256))throw Error('Falta el texto original del bloque guardado.');
   return {page:reference.page,text:workspace.texts[source.sha256]};
  });
  return result;
 }
 function list(state){
  const workspace=state.authoringWorkspace;
  const values=workspace?Object.values(workspace.blocks):state.authoring?[state.authoring]:[];
  return values.map(block=>({sha256:block.sha256,title:block.request.identity.name,scope:block.request.scope,
   version:block.request.identity.version,status:block.report.status})).sort((a,b)=>{
    if(a.sha256===b.sha256)return 0;
    if(a.sha256===workspace?.latest)return -1;if(b.sha256===workspace?.latest)return 1;return a.sha256.localeCompare(b.sha256);
   });
 }
 return {record,list};
});
