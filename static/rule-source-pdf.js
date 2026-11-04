/* PDF source reader. Local files only; no API, AI, database or document scripts. */
(function(root,factory){const value=factory();if(typeof module==='object'&&module.exports)module.exports=value;else root.RuleSourcePDF=value})(typeof window==='object'?window:globalThis,()=>{
 const VERSION='6.5.438',BASE='/vendor/pdfjs-'+VERSION+'/',MAX_BYTES=128*1024*1024,MAX_PAGES=2500;
 let library;
 function parsePages(text,total){
  if(typeof text!=='string'||!text.trim()||text.length>250)throw Error('Indica páginas, por ejemplo: 1, 4-6.');
  const result=new Set();
  for(const part of text.split(',')){
   const match=/^\s*(\d+)\s*(?:-\s*(\d+)\s*)?$/.exec(part);if(!match)throw Error('La selección de páginas no es válida.');
   const low=Number(match[1]),high=Number(match[2]||match[1]);
   if(!Number.isSafeInteger(low)||!Number.isSafeInteger(high)||low<1||high<low||high>total||high-low>=32)throw Error('Selecciona hasta 32 páginas existentes.');
   for(let n=low;n<=high;n++)result.add(n);
   if(result.size>32)throw Error('Selecciona hasta 32 páginas por preparación.');
  }
  return [...result].sort((a,b)=>a-b);
 }
 function textFromItems(items){
  let text='';
  for(const item of items){
   if(typeof item.str!=='string')continue;
   text+=item.str+(item.hasEOL?'\n':' ');
   if(text.length>24000)throw Error('La página supera los 24.000 caracteres del bloque; selecciona un fragmento de texto más acotado.');
  }
  text=text.replace(/[ \t]+\n/g,'\n').trim();
  if(!text)throw Error('La página no contiene texto extraíble. No hay OCR: aporta una transcripción verificable.');
  return text;
 }
 async function pdfLibrary(){
  if(!library)library=import(BASE+'build/pdf.min.mjs').then(pdf=>{pdf.GlobalWorkerOptions.workerSrc=BASE+'build/pdf.worker.min.mjs';return pdf}).catch(error=>{library=null;throw error});
  return library;
 }
 async function open(file){
  if(!file||!Number.isFinite(file.size)||file.size<8||file.size>MAX_BYTES)throw Error('Selecciona un PDF de hasta 128 MiB.');
  const bytes=new Uint8Array(await file.arrayBuffer());
  if(String.fromCharCode(...bytes.slice(0,5))!=='%PDF-')throw Error('El archivo no tiene una cabecera PDF válida.');
  const sha256=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('');
  const pdf=await pdfLibrary();
  const task=pdf.getDocument({data:bytes,isEvalSupported:false,enableXfa:false,stopAtErrors:true,
   cMapUrl:BASE+'cmaps/',cMapPacked:true,standardFontDataUrl:BASE+'standard_fonts/',wasmUrl:BASE+'wasm/',
   useSystemFonts:false,disableAutoFetch:true});
  let password=false;
  task.onPassword=()=>{password=true;task.destroy().catch(()=>{});};
  let document;
  try{document=await task.promise;}catch{
   await task.destroy().catch(()=>{});
   throw Error(password?'El PDF requiere contraseña. Aporta una copia que puedas abrir sin contraseña.':'No se ha podido leer este PDF. El original no se ha modificado.');
  }
  if(document.numPages>MAX_PAGES){await task.destroy();throw Error('El PDF supera las 2.500 páginas admitidas en esta versión.');}
  const cache=new Map();let closed=false,renderTask,renderSequence=0,extractions=0;
  async function pageText(number){
   if(closed)throw Error('Vuelve a seleccionar el PDF para consultarlo.');
   if(!Number.isInteger(number)||number<1||number>document.numPages)throw Error('Página PDF fuera de límites.');
   if(!cache.has(number)){
    const pending=(async()=>{const page=await document.getPage(number),content=await page.getTextContent();extractions++;return textFromItems(content.items);})();
    cache.set(number,pending);pending.catch(()=>{if(cache.get(number)===pending)cache.delete(number);});
    if(cache.size>64){const first=[...cache.keys()].find(n=>n!==number);cache.delete(first);}
   }
   return cache.get(number);
  }
  return {sha256,pageCount:document.numPages,name:file.name||'Documento PDF',get extractions(){return extractions},
   pageText,
   async select(selection){
    const numbers=parsePages(selection,document.numPages),pages=[];let size=0;
    for(const number of numbers){const text=await pageText(number);size+=text.length;if(size>24000)throw Error('Las páginas seleccionadas superan los 24.000 caracteres. Reduce el bloque.');pages.push({page:number,text});}
    return {pages,origin:{kind:'pdf',sha256,pageCount:document.numPages,extractor:'pdfjs-'+VERSION}};
   },
   async render(number,canvas){
    const sequence=++renderSequence;renderTask?.cancel();
    if(closed||!Number.isInteger(number)||number<1||number>document.numPages)throw Error('Página PDF fuera de límites.');
    const page=await document.getPage(number);if(sequence!==renderSequence||closed)return;
    const unit=page.getViewport({scale:1}),scale=Math.min(1200/unit.width,Math.sqrt(2000000/(unit.width*unit.height))),viewport=page.getViewport({scale});
    canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
    renderTask=page.render({canvasContext:canvas.getContext('2d'),viewport});
    try{await renderTask.promise;}catch(error){if(error.name!=='RenderingCancelledException')throw error;}
   },
   async destroy(){if(closed)return;closed=true;renderSequence++;renderTask?.cancel();cache.clear();await task.destroy();}
  };
 }
 return {open,parsePages,textFromItems,version:VERSION,maxBytes:MAX_BYTES};
});
