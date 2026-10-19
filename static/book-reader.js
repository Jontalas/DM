/* On-demand private pages. Persistent bounded browser cache, never whole PDFs. */
(function(root){
 'use strict';
 const DB='cronicas-reader-v1',MAX_PAGES=50,MAX_BYTES=32*1024*1024;
 let database;
 function db(){
  if(!database)database=new Promise(resolve=>{
   try{
    const request=indexedDB.open(DB,1);
    request.onupgradeneeded=()=>request.result.createObjectStore('pages',{keyPath:'id'});
    request.onsuccess=()=>{request.result.onversionchange=()=>request.result.close();resolve(request.result)};
    request.onerror=request.onblocked=()=>resolve(null);
   }catch{resolve(null)}
  });
  return database;
 }
 const memory=new Map();let memoryBytes=0;
 function remember(record){
  const old=memory.get(record.id);if(old)memoryBytes-=old.blob.size;
  memory.delete(record.id);memory.set(record.id,record);memoryBytes+=record.blob.size;
  while(memory.size>MAX_PAGES||memoryBytes>MAX_BYTES){const [id,value]=memory.entries().next().value;memory.delete(id);memoryBytes-=value.blob.size}
 }
 async function cached(id){
  if(memory.has(id)){const value=memory.get(id);memory.delete(id);memory.set(id,value);return value.blob}
  const database=await db();if(!database)return null;
  return new Promise(resolve=>{
   try{const request=database.transaction('pages','readonly').objectStore('pages').get(id);request.onsuccess=()=>{if(request.result)remember(request.result);resolve(request.result?.blob||null)};request.onerror=()=>resolve(null)}catch{resolve(null)}
  });
 }
 async function save(id,blob){
  const record={id,blob,lastUsed:Date.now()};remember(record);
  const database=await db();if(!database)return;
  await new Promise(resolve=>{
   try{
    const transaction=database.transaction('pages','readwrite'),store=transaction.objectStore('pages');
    store.put(record);const request=store.getAll();
    request.onsuccess=()=>{
     const records=request.result.sort((a,b)=>b.lastUsed-a.lastUsed);let bytes=0;
     records.forEach((item,i)=>{bytes+=item.blob.size;if(i>=MAX_PAGES||bytes>MAX_BYTES)store.delete(item.id)});
    };
    transaction.oncomplete=transaction.onerror=transaction.onabort=()=>resolve();
   }catch{resolve()}
  });
 }
 async function clear(){
  memory.clear();memoryBytes=0;const database=await db();if(!database)return;
  await new Promise(resolve=>{try{const tx=database.transaction('pages','readwrite');tx.objectStore('pages').clear();tx.oncomplete=tx.onerror=tx.onabort=()=>resolve()}catch{resolve()}});
 }
 async function owner(token){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token)))].map(x=>x.toString(16).padStart(2,'0')).join('')}
 function mount({token,image,status,input,total,previous,next}){
  let generation=0,controller,url,zoom=100;const manifests=new Map();
  async function request(path,session,signal){
   const response=await fetch(path,{headers:{Authorization:'Bearer '+session},signal,cache:'no-store'});
   if(!response.ok){let message='No se pudo cargar esta página';try{message=(await response.json()).error||message}catch{}throw Error(message)}
   return response;
  }
  async function manifest(book,session){
   const key=session+':'+book,old=manifests.get(key);
   if(old&&old.expires>Date.now())return old.promise;
   const promise=request('/api/book-info?book='+encodeURIComponent(book),session).then(response=>response.json());
   manifests.set(key,{promise,expires:Date.now()+60000});
   try{return await promise}catch(error){manifests.delete(key);throw error}
  }
  async function open(book,page){
   if(!token())return;
   if(!Number.isInteger(page)||page<1){status.textContent='Indica una página válida';return}
   const serial=++generation,session=token();controller?.abort();const currentController=new AbortController();controller=currentController;
   image.hidden=true;status.textContent='Cargando página '+page+'…';previous.disabled=next.disabled=true;
   try{
    const info=await manifest(book,session);if(serial!==generation)return;
    if(page>info.pages)throw Error('Este manual tiene '+info.pages+' páginas');
    const key=await owner(session)+':'+book+':'+info.revision+':'+page;
    let blob=await cached(key);const reused=!!blob;
    if(serial!==generation||session!==token())return;
    if(!blob){const extension=info.format==='webp'?'webp':'jpg';const response=await request('/book-pages/'+book+'/'+info.revision+'/'+page+'.'+extension,session,currentController.signal);blob=await response.blob();if(!['image/jpeg','image/webp'].includes(blob.type)||blob.size>8*1024*1024)throw Error('Formato de página no válido')}
    if(serial!==generation||session!==token())return;
    if(url)URL.revokeObjectURL(url);url=URL.createObjectURL(blob);
    image.alt='Página '+page+' del manual '+book;image.src=url;
    await image.decode();if(serial!==generation||session!==token())return;
    if(!reused)await save(key,blob);
    if(serial!==generation)return;
    input.value=String(page);input.max=String(info.pages);total.textContent='/ '+info.pages;
    image.hidden=false;image.style.width=zoom+'%';previous.disabled=page<=1;next.disabled=page>=info.pages;
    status.textContent='Página '+page+' · '+(reused?'copia guardada en este navegador':Math.ceil(blob.size/1024)+' KB · guardada para reutilizar');
   }catch(error){if(serial===generation&&error.name!=='AbortError')status.textContent=error.message}
  }
  function setZoom(value){zoom=Math.max(50,Math.min(300,value));image.style.width=zoom+'%'}
  async function reset(){generation++;controller?.abort();manifests.clear();if(url)URL.revokeObjectURL(url);url=null;image.removeAttribute('src');image.hidden=true;await clear()}
  return {open,reset,zoom:delta=>setZoom(zoom+delta),fit:()=>setZoom(100),clear};
 }
 root.BookReader={mount};
})(window);
