// Isolated provider fixture, not a real AI quality evaluation.
const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{
  env:{...process.env,TEST_ADVENTURE_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const host=await browser.newContext(),guest=await browser.newContext();
  for(const context of [host,guest])await context.route('**/api/status',async route=>{
   const response=await route.fetch();await route.fulfill({json:{...await response.json(),aiConfigured:true}});
  });
  const token=(await (await host.request.post(url+'/api/create',{data:{player:'Ana',title:'Adventure fixture',goal:'Investigar las luces'}})).json()).token;
  const headers={Authorization:'Bearer '+token};
  const catalog=require('./static/creation-catalog.json');
  const choices={...catalog.presets.guardian,name:'Aria',race:'human',class:'fighter',level:1,favored:'hp',feats:['focus','initiative','toughness'],skills:['climb','intimidate','perception'],languages:[]};
  let room=await (await host.request.get(url+'/api/state',{headers})).json();
  const player=(await (await guest.request.post(url+'/api/join',{data:{name:'Luis',invite:room.invite}})).json()).token;
  room=await (await host.request.get(url+'/api/state',{headers})).json();
  assert.ok((await host.request.post(url+'/api/action',{headers,data:{id:'fixture-hero',version:room.version,type:'create_character',choices}})).ok());
  await host.addInitScript(t=>localStorage.setItem('cronicas-token',t),token);
  await guest.addInitScript(t=>localStorage.setItem('cronicas-token',t),player);
  const a=await host.newPage(),b=await guest.newPage(),errors=[],actions=[];
  for(const page of [a,b])page.on('pageerror',error=>errors.push(error.message));
  a.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await a.goto(url);await a.locator('#beginAdventure').waitFor();
  await a.locator('#beginAdventure').click();await a.locator('#adventureForm').waitFor();
  assert.equal(actions.length,0);
  assert.equal(await a.locator('#adventureForm [name=source]').inputValue(),'example');
  await a.locator('#adventureForm [name=source]').selectOption('generated');
  await a.locator('#adventureForm [name=premise]').fill('Investigar las luces del molino');
  await a.locator('#adventureForm button').click();await a.locator('#modal').waitFor({state:'hidden'});
  assert.equal(actions.length,1);assert.equal(actions[0].type,'start_adventure');
  await a.locator('nav [data-tab=journal]').click();
  assert.match(await a.locator('#adventureSummary').textContent(),/puerta sigue cerrada/);
  assert.equal(await a.locator('#directorMemoryDetails').isVisible(),true);
  await b.goto(url);await b.locator('#app').waitFor({state:'visible'});
  await b.locator('nav [data-tab=journal]').click();
  assert.equal(await b.locator('#directorMemoryDetails').isVisible(),false);
  const guestState=await (await guest.request.get(url+'/api/state',{headers:{Authorization:'Bearer '+player}})).json();
  assert.ok(!JSON.stringify(guestState).includes('bajo la escalera'));
  await a.locator('nav [data-tab=story]').click();
  await a.locator('#message').fill('Intento abrir la puerta');await a.locator('#send').click();
  await a.locator('[data-resolve-check]').waitFor();
  assert.equal(await a.locator('#continueAdventure').isVisible(),false);
  await a.locator('[data-resolve-check]').click();await a.locator('#continueAdventure').waitFor();
  await a.locator('#continueAdventure').click();
  await a.waitForFunction(()=>snapshot.state.adventure.revision===2);
  assert.equal(await a.locator('#continueAdventure').isVisible(),false);
  assert.deepEqual(actions.map(item=>item.type),['start_adventure','talk','check','continue_adventure']);
  await a.reload();await a.locator('#app').waitFor({state:'visible'});
  assert.equal(await a.locator('#beginAdventure').count(),0);
  await a.locator('nav [data-tab=journal]').click();
  assert.match(await a.locator('#adventureSummary').textContent(),/superar la prueba/);
  await a.setViewportSize({width:390,height:844});
  assert.ok(await a.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await a.screenshot({path:'.deps/adventure-mobile.png',fullPage:true});
  if(process.env.TEST_DIRECTOR_ERROR_UI==='1'){
   const before=await a.evaluate(()=>({version:snapshot.version,state:structuredClone(snapshot.state)})),stage=process.env.TEST_DIRECTOR_ERROR_STAGE||'narration',diagnostic=(stage==='output_limit'?'El director agotó el límite de salida antes de completar la aventura.':stage==='module'?'El director entregó una aventura incompatible: campo de prueba.':'Claude Haiku no entregó una respuesta completa y válida.')+' La acción no se ha aplicado (director:'+stage+')';
   await a.route('**/api/action',route=>route.fulfill({status:400,json:{error:diagnostic}}),{times:1});await a.locator('[data-tab=story]').click();await a.locator('#message').fill('Mi declaración pendiente de revisar.');await a.locator('#send').click();await a.waitForFunction(()=>!busy);assert.equal(await a.locator('#directorIssue').count(),1,'A rejected director response needs a reviewable explanation');assert.equal(await a.locator('#message').inputValue(),'Mi declaración pendiente de revisar.');assert.equal(await a.evaluate(()=>localStorage.getItem('cronicas-pending')),null);assert.deepEqual(await a.evaluate(()=>({version:snapshot.version,state:structuredClone(snapshot.state)})),before);assert.doesNotMatch(await a.locator('#toast').textContent(),/director:/);
   await a.locator('[data-tab=journal]').click();assert.equal(await a.locator('#directorIssue').evaluate(element=>element.open),false);const count=actions.length;await a.locator('#directorIssue > summary').focus();await a.keyboard.press('Enter');assert.match(await a.locator('#directorIssue').textContent(),/nuevo envío/);await a.locator('#directorIssue details > summary').focus();await a.keyboard.press('Enter');assert.match(await a.locator('#directorIssue details').textContent(),new RegExp('director:'+stage));assert.equal(actions.length,count);assert.ok(await a.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await a.locator('[data-tab=story]').click();await a.locator('#messageKind').selectOption('ooc');await a.locator('#useAI').uncheck();await a.locator('#message').fill('Comentario de prueba sin director.');await a.locator('#send').click();await a.waitForFunction(v=>snapshot.version>v&&!busy,before.version);assert.equal(await a.locator('#directorIssue').count(),0,'A later successful intervention clears the old notice');await a.locator('#messageKind').selectOption('action');await a.locator('#useAI').check();
  }
  if(process.env.TEST_EXCEPTION_UI==='1'){
   const before=await a.evaluate(()=>structuredClone(snapshot.state.characters));await a.locator('[data-tab=story]').click();await a.locator('#message').fill('Acción técnica fuera de cobertura');await a.locator('#send').click();await a.waitForFunction(()=>!busy);assert.equal(await a.evaluate(()=>snapshot.state.pending.length),1,JSON.stringify(await a.evaluate(()=>({toast:document.querySelector('#toast').textContent,ai:document.querySelector('#useAI').checked,last:snapshot.state.messages.at(-1).kind}))));assert.deepEqual(await a.evaluate(()=>snapshot.state.characters),before);
   await b.evaluate(()=>refresh(true));await b.setViewportSize({width:390,height:844});await b.locator('[data-tab=journal]').click();assert.equal(await b.locator('#pending [data-pending]').count(),0,'A guest must not be offered an unauthorized resolution');assert.match(await b.locator('#pending').textContent(),/anfitrión/);assert.equal(await b.locator('.pending-resolution details').evaluate(element=>element.open),false);await b.locator('#journalPending').scrollIntoViewIfNeeded();await b.screenshot({path:'.deps/exception-guest-mobile.png'});const guestPosts=[];b.on('request',request=>{if(request.method()==='POST')guestPosts.push(request.url())});await b.evaluate(()=>manualForm(0));assert.equal(await b.locator('#manualForm').count(),0);assert.equal(guestPosts.length,0);
   await a.locator('#playGuidanceAction').click();assert.equal(await a.locator('#journalPending h3').evaluate(element=>element===document.activeElement),true);await a.locator('#pending [data-pending="0"]').click();await a.locator('#manualForm [name=reference]').fill('Fixture de interfaz, sin regla verificada');await a.locator('#manualForm [name=resolution]').fill('Resolución excepcional de prueba sin cambios de ficha.');
   await a.evaluate(()=>act('talk',{text:'Acción técnica fuera de cobertura',kind:'action',director:true}));assert.equal(await a.evaluate(()=>snapshot.state.pending.length),2);const count=actions.length;await a.locator('#manualForm button').click();await a.waitForFunction(()=>!busy);assert.equal(actions.length,count,'An outdated pending list must not resolve a different entry');assert.match(await a.locator('#manualProgress').textContent(),/pendientes han cambiado/);assert.equal(await a.evaluate(()=>snapshot.state.pending.length),2);
   await a.locator('#closeModal').click();await a.locator('#pending [data-pending="0"]').click();await a.locator('#manualForm [name=reference]').fill('Fixture de interfaz, sin regla verificada');await a.locator('#manualForm [name=resolution]').fill('Resolución excepcional de prueba sin cambios de ficha.');
   let sent,release;const requested=new Promise(resolve=>{sent=resolve}),gate=new Promise(resolve=>{release=resolve});await a.route('**/api/action',async route=>{const response=await route.fetch();assert.equal(response.status(),200);sent();await gate;await route.fulfill({response})},{times:1});await a.evaluate(()=>{const form=document.querySelector('#manualForm'),handler=form.onsubmit;form.onsubmit=event=>{window.manualFinished=handler(event);return window.manualFinished}});await a.locator('#manualForm button').click();await requested;assert.equal(await a.locator('#manualForm input:enabled, #manualForm select:enabled, #manualForm textarea:enabled, #manualForm button:enabled').count(),0);await a.locator('#closeModal').click();await a.locator('#libraryBtn').click();release();await a.evaluate(()=>window.manualFinished);assert.equal(await a.locator('#modal').evaluate(element=>element.open),true);assert.match(await a.locator('#modalContent h2').textContent(),/Partidas y personajes/);await a.locator('#closeModal').click();
   assert.equal(await a.evaluate(()=>snapshot.state.pending.length),1);assert.deepEqual(await a.evaluate(()=>snapshot.state.characters),before);assert.equal(actions.at(-1).type,'manual');assert.equal(actions.at(-1).pendingIndex,0);assert.ok(await a.evaluate(()=>snapshot.state.messages.at(-1).text.includes('Resolución excepcional de prueba')));
  }
  if(process.env.TEST_DIRECTOR_ERROR_UI==='1'){
   await a.route('**/api/action',route=>route.fulfill({status:400,json:{error:'Respuesta de prueba. La acción no se ha aplicado (director:narration)'}}),{times:1});await a.locator('[data-tab=story]').click();await a.locator('#message').fill('Otro intento de prueba rechazado.');await a.locator('#send').click();await a.waitForFunction(()=>!busy&&!!document.querySelector('#directorIssue'));const campaign=await a.evaluate(()=>snapshot.id);await a.locator('#exitBtn').click();await a.locator('#createForm [name=player]').fill('Eva');await a.locator('#createForm button').click();await a.waitForFunction(id=>snapshot.id!==id&&!busy,campaign);assert.equal(await a.locator('#directorIssue').count(),0,'Director diagnostics must not cross into a different campaign');
  }
  assert.deepEqual(errors,[]);
  console.log('OK: start, memory, secret isolation, check-to-narration, no duplicate calls, reload and mobile. Provider simulated.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
