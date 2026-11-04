/* Only the currently consulted local PDF is retained in memory. */
window.RuleSourcePDFUI=(()=>{
 let active,loadSequence=0;
 async function load(file,scope,expected,ensure=()=>{}){
  const sequence=++loadSequence;
  const session=await RuleSourcePDF.open(file);
  try{ensure();if(sequence!==loadSequence)throw Error('Hay otra lectura de PDF más reciente.');}catch(error){await session.destroy();throw error;}
  if(expected&&session.sha256!==expected){await session.destroy();throw Error('La huella del PDF no coincide con el original de esta preparación.');}
  if(active?.scope===scope&&active.session.sha256===session.sha256){await session.destroy();return active;}
  if(active)await active.session.destroy();
  active={scope,session,source:null,selection:'1',use:true};return active;
 }
 function mount(form,scope,ensure){
  let mode=false,selected=null,loading=false,revision=0;
  const tools=document.createElement('section');tools.className='pack-pdf-tools';
  tools.innerHTML='<label>Leer un PDF local, opcional<input id="packPdfFile" type="file" accept=".pdf,application/pdf"></label><small id="packPdfStatus" role="status">El PDF permanece en este navegador; solo se enviarán los textos seleccionados.</small><div id="packPdfControls" hidden><label>Páginas para preparar<input id="packPdfSelection" placeholder="Por ejemplo: 1, 4-6"></label><button type="button" id="packPdfSelect">Usar estas páginas</button><label>Consultar página original<input id="packPdfViewPage" type="number" min="1" step="1"></label><canvas id="packPdfCanvas" class="pack-pdf-canvas" aria-label="Página del PDF original"></canvas><p class="hint">La numeración corresponde al archivo PDF, no al folio impreso. Comprueba las columnas y tablas en el original: la extracción de texto puede alterar su disposición. No hay OCR.</p><button type="button" id="packPdfClear">Volver al texto aportado</button></div>';
  form.querySelector('#packSourceFile').closest('label').before(tools);
  const controls=tools.querySelector('#packPdfControls'),status=tools.querySelector('#packPdfStatus'),pageInput=tools.querySelector('#packPdfViewPage');
  const selection=tools.querySelector('#packPdfSelection'),canvas=tools.querySelector('canvas');
  function clear(){revision++;mode=false;selected=null;loading=false;if(active?.scope===scope)active.use=false;controls.hidden=true;form.elements.text.readOnly=false;form.elements.page.readOnly=false;}
  function apply(source){
   selected=structuredClone(source);mode=true;
   form.elements.text.value=source.pages.map(p=>'[PDF p.'+p.page+']\n'+p.text).join('\n\n');
   form.elements.text.readOnly=true;form.elements.page.value=source.pages[0].page;form.elements.page.readOnly=true;
   form.dispatchEvent(new Event('input'));
  }
  async function show(current){
   mode=true;current.use=true;controls.hidden=false;selection.value=current.selection;pageInput.max=current.session.pageCount;pageInput.value=current.source?.pages[0]?.page||1;
   status.textContent=current.session.pageCount+' páginas · archivo local SHA-256 '+current.session.sha256;
   if(current.source)apply(current.source);
   await current.session.render(Number(pageInput.value),canvas);
  }
  tools.querySelector('#packPdfFile').onchange=run(async e=>{
   const file=e.target.files[0];if(!file)return;
   const attempt=++revision;loading=true;status.textContent='Leyendo el PDF local…';
   try{const current=await load(file,scope,null,ensure);if(attempt!==revision||!form.isConnected)return;
    selected=null;form.elements.text.value='';loading=false;await show(current);
   }finally{if(attempt===revision)loading=false;}
  });
  tools.querySelector('#packPdfSelect').onclick=run(async()=>{
   ensure();if(!active||active.scope!==scope||loading)throw Error('Espera a que se lea el PDF.');
   const requested=selection.value,attempt=++revision;selected=null;
   const source=await active.session.select(requested);ensure();if(attempt!==revision||selection.value!==requested)return;
   active.source=source;active.selection=requested;apply(source);pageInput.value=source.pages[0].page;
   await active.session.render(source.pages[0].page,canvas);
   if(attempt===revision)status.textContent='Selección lista: páginas '+source.pages.map(p=>p.page).join(', ')+'. Solo estos fragmentos se usarán para preparar reglas.';
  });
  selection.oninput=()=>{revision++;selected=null;form.elements.text.value='';form.elements.text.readOnly=true;status.textContent='Usa la nueva selección antes de preparar sus reglas.';};
  pageInput.onchange=run(async()=>{ensure();if(active?.scope===scope)await active.session.render(Number(pageInput.value),canvas);});
  tools.querySelector('#packPdfClear').onclick=()=>{clear();form.elements.text.value='';form.dispatchEvent(new Event('input'));};
  if(active?.scope===scope&&active.use)run(()=>show(active))();
  return {clear,document(){
   if(loading)throw Error('Espera a que termine la lectura del PDF.');
   if(mode&&!selected)throw Error('Selecciona las páginas del PDF antes de preparar sus reglas.');
   return selected?structuredClone(selected):null;
  }};
 }
 function openOriginal(record,scope,ensure,back){
  const origin=record.request.document.origin;if(!origin)return;
  modal(`<div class="eyebrow">ORIGINAL LOCAL · SIN IA</div><h2>Consultar el PDF de la preparación</h2><p>La copia binaria no se guarda en Firebase. Si has recargado o cambiado de documento, selecciona el mismo archivo; se comprobará su huella.</p><label>PDF original<input id="packOriginalFile" type="file" accept=".pdf,application/pdf"></label><label>Página PDF<input id="packOriginalPage" type="number" min="1" max="${origin.pageCount}" value="${record.request.document.pages[0].page}" step="1"></label><canvas id="packOriginalCanvas" class="pack-pdf-canvas" aria-label="Original de la preparación"></canvas><small id="packOriginalStatus" role="status"></small><button id="packOriginalBack" type="button">Volver al informe</button>`);
  const canvas=$('#packOriginalCanvas'),page=$('#packOriginalPage'),status=$('#packOriginalStatus');
  async function show(){ensure();if(active?.scope!==scope||active.session.sha256!==origin.sha256){status.textContent='Selecciona el PDF original para mostrar esta página.';return;}
   await active.session.render(Number(page.value),canvas);status.textContent='Archivo coincidente · SHA-256 '+origin.sha256;
  }
  $('#packOriginalFile').onchange=run(async e=>{const file=e.target.files[0];if(!file)return;await load(file,scope,origin.sha256,ensure);await show();});
  page.onchange=run(show);$('#packOriginalBack').onclick=back;run(show)();
 }
 return {mount,openOriginal};
})();
