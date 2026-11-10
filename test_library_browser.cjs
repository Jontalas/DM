const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn,execFileSync}=require('node:child_process'),{createInterface}=require('node:readline');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext({acceptDownloads:true});
  const first=(await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'La primera campaña',goal:'Investigar'}})).json()).token;
  const headers={Authorization:'Bearer '+first},catalog=require('./static/creation-catalog.json');
  const choices={...catalog.presets.guardian,name:'Aria',race:'human',class:'fighter',level:1,favored:'hp',feats:['focus','initiative','toughness'],skills:['climb','intimidate','perception'],languages:[]};
  let room=await (await context.request.get(url+'/api/state',{headers})).json();
  assert.ok((await context.request.post(url+'/api/action',{headers,data:{type:'create_character',id:'hero',version:room.version,choices}})).ok());
  room=await (await context.request.get(url+'/api/state',{headers})).json();
  const originalCharacter=room.state.characters[0];
  assert.ok((await context.request.post(url+'/api/action',{headers,data:{type:'manual',id:'fixture-injury',version:room.version,character:originalCharacter.id,hpDelta:-5,reason:'Fixture de continuidad',resolution:'Solo datos de prueba'}})).ok());
  const page=await context.newPage(),errors=[],actions=[];let stateReads=0;
  page.on('pageerror',error=>errors.push(error.message));page.on('request',r=>{if(new URL(r.url()).pathname==='/api/state')stateReads++;if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  if(process.env.TEST_LIBRARY_ENTRY_BASELINE==='1')await page.route('**/campaign-library-ui.js*',route=>route.fulfill({contentType:'text/javascript',body:execFileSync('git',['show','4fd5e0681a3e536ab6a4a034e38e46c9274f216f:static/campaign-library-ui.js'],{encoding:'utf8'})}));
  await page.goto(url);await page.evaluate(t=>localStorage.setItem('cronicas-token',t),first);await page.reload();
  await page.locator('#app').waitFor({state:'visible'});await page.locator('#exitBtn').click();
  assert.equal(await page.locator('#savedLibraryPanel').evaluate(el=>el.open),true);
  assert.match(await page.locator('#savedCampaigns').textContent(),/Aria/);
  await page.locator('#campaignOptions > summary').click();
  await page.locator('#createForm [name=title]').fill('La segunda campaña');
  await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Otra historia');
  await page.locator('#createForm button').click();await page.locator('#app').waitFor({state:'visible'});
  if(process.env.TEST_LIBRARY_ENTRY_COORDINATION==='1'){
   const before=await page.evaluate(()=>({snapshot:structuredClone(snapshot),token})),destination=room.id+':'+room.me.id;let requested,release;const readRequested=new Promise(resolve=>{requested=resolve}),readGate=new Promise(resolve=>{release=resolve});let reads=0;
   await page.route('**/api/state',async route=>{reads++;const response=await route.fetch();assert.equal(response.status(),200);requested();await readGate;await route.fulfill({response})},{times:1});
   const beforeReads=stateReads;const opening=page.evaluate(id=>openSavedCampaign(id),destination);opening.catch(()=>{});await readRequested;
   assert.equal(await page.evaluate(t=>token===t,before.token),true,'Keep the displayed campaign access until the replacement state is validated');assert.deepEqual(await page.evaluate(()=>snapshot.state),before.snapshot.state);assert.equal(await page.evaluate(()=>busy),true);
   const blocked=await page.evaluate(async id=>{try{await openSavedCampaign(id);return false}catch{return true}},destination);assert.equal(blocked,true);assert.equal(reads,1);await page.evaluate(()=>document.querySelector('#resume').onclick());assert.equal(stateReads,beforeReads+1,'Resume must not load another state during an entry already in progress');
   const beforeAction=actions.length;assert.equal(await page.evaluate(async()=>{try{await act('roll',{expression:'1d20'});return false}catch{return true}}),true);assert.equal(actions.length,beforeAction);
   await page.locator('#libraryBtn').click();release();await opening;assert.equal(await page.evaluate(()=>snapshot.id),room.id);assert.equal(await page.locator('#modal').evaluate(e=>e.open),true,'Opening a saved campaign must preserve a newer dialog');assert.match(await page.locator('#modalContent h2').textContent(),/Partidas y personajes/);
   await page.locator('#closeModal').click();await page.evaluate(id=>openSavedCampaign(id),before.snapshot.id+':'+before.snapshot.me.id);assert.equal(await page.evaluate(()=>snapshot.id),before.snapshot.id);assert.equal(await page.evaluate(()=>busy),false);
   await page.route('**/api/state',route=>route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({error:'Este acceso de prueba no está disponible.'})}),{times:1});assert.equal(await page.evaluate(async id=>{try{await openSavedCampaign(id);return false}catch{return true}},destination),true);assert.equal(await page.evaluate(t=>token===t,before.token),true);assert.equal(await page.evaluate(()=>snapshot.id),before.snapshot.id);assert.equal(await page.evaluate(()=>busy),false);

  }
  await page.locator('#libraryBtn').click();
  assert.equal(await page.locator('#modal .library-entry').count(),2);
  assert.equal(await page.locator('[data-library-copy]').isVisible(),false);
  const beforeExpand=actions.length,firstCharacter=page.locator('#modal .library-entry').filter({has:page.locator('[data-library-copy]')});await firstCharacter.locator('.library-characters>summary').focus();await page.keyboard.press('Enter');assert.equal(await page.locator('[data-library-copy]').isVisible(),true);assert.equal(actions.length,beforeExpand);
  await page.locator('[data-library-copy]').click();await page.locator('#copyLibraryCharacter [name=name]').fill('Aria segunda');
  await page.locator('#copyLibraryCharacter button').click();await page.locator('.sheet-checks').waitFor();
  assert.deepEqual(actions.map(a=>a.type),['create_character']);
  let second=await page.evaluate(()=>({id:snapshot.id,char:snapshot.state.characters[0]}));
  assert.notEqual(second.char.id,originalCharacter.id);assert.equal(second.char.hp,originalCharacter.maxHp);
  await page.locator('#closeModal').click();await page.locator('#libraryBtn').click();
  const sourceId=room.id+':'+room.me.id;
  await page.locator(`#modal [data-library-entry="${sourceId}"] .library-characters>summary`).click();await page.locator(`#modal [data-library-open="${sourceId}"][data-library-character]`).click();
  await page.locator('.sheet-checks').waitFor();
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hp),originalCharacter.maxHp-5);
  await page.locator('#closeModal').click();await page.locator('#libraryBtn').click();
  const pending={token:first,body:{id:'not-sent',type:'roll'}};
  await page.evaluate(value=>localStorage.setItem('cronicas-pending',JSON.stringify(value)),pending);
  await page.locator('#modal [data-library-open]').first().click();
  assert.match(await page.locator('#toast').textContent(),/envío pendiente/);
  assert.equal(await page.evaluate(()=>snapshot.id),room.id);
  await page.evaluate(()=>localStorage.removeItem('cronicas-pending'));
  await page.locator('#libraryAccessTools>summary').click();
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportAccesses').click()]);
  const backupPath=await download.path();
  assert.ok(backupPath);
  const restoredContext=await browser.newContext(),restored=await restoredContext.newPage();
  await restored.goto(url);await restored.locator('#savedLibraryPanel > summary').click();await restored.locator('#manageAccesses').click();
  await restored.locator('#libraryAccessTools>summary').click();
  if(process.env.TEST_ACCESS_IMPORT_ASYNC==='1'){
   await restored.evaluate(()=>{window.originalAccessText=File.prototype.text;File.prototype.text=function(){if(this.name!=='slow-accesses.json')return window.originalAccessText.call(this);return new Promise(resolve=>{window.releaseAccessRead=()=>window.originalAccessText.call(this).then(resolve)})};const input=document.querySelector('#importAccesses'),handler=input.onchange;input.onchange=e=>{window.accessReadFinished=handler(e);return window.accessReadFinished}});
   await restored.locator('#importAccesses').setInputFiles({name:'slow-accesses.json',mimeType:'application/json',buffer:fs.readFileSync(backupPath)});await restored.waitForFunction(()=>!!window.releaseAccessRead);await restored.locator('#closeModal').click();await restored.locator('#manageAccesses').click();await restored.evaluate(()=>document.querySelector('#modalContent').firstElementChild.dataset.newDialog='true');
   await restored.evaluate(()=>window.releaseAccessRead());await restored.evaluate(()=>window.accessReadFinished);assert.equal(await restored.evaluate(()=>CampaignLibrary.read(localStorage).entries.length),0,'Closing an access-file read before it completes must not import credentials');assert.equal(await restored.locator('#modalContent').evaluate(e=>e.firstElementChild.dataset.newDialog), 'true');assert.equal(await restored.locator('#modal').evaluate(e=>e.open),true);await restored.evaluate(()=>{File.prototype.text=window.originalAccessText});
   await restored.locator('#libraryAccessTools>summary').click();await restored.locator('#importAccesses').setInputFiles({name:'unreadable-accesses.json',mimeType:'application/json',buffer:Buffer.from('{not a backup')});await restored.waitForFunction(()=>document.querySelector('#accessImportStatus')?.textContent.includes('No se puede leer'));assert.equal(await restored.locator('#importAccesses').inputValue(),'');assert.equal(await restored.evaluate(()=>CampaignLibrary.read(localStorage).entries.length),0);
  }
  await restored.locator('#importAccesses').setInputFiles(backupPath);
  await restored.waitForFunction(()=>document.querySelectorAll('#modal .library-entry').length===2);
  await restored.locator(`#modal [data-library-entry="${sourceId}"] .library-characters>summary`).click();await restored.locator(`#modal [data-library-open="${sourceId}"][data-library-character]`).click();
  await restored.locator('.sheet-checks').waitFor();
  assert.equal(await restored.evaluate(()=>snapshot.state.characters[0].hp),originalCharacter.maxHp-5);
  await page.reload();await page.locator('#app').waitFor({state:'visible'});
  await page.locator('#libraryBtn').click();assert.equal(await page.locator('#modal .library-entry').count(),2);
  await page.setViewportSize({width:390,height:844});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.ok(await page.locator('#modal').evaluate(el=>el.scrollWidth<=el.clientWidth));
  await page.screenshot({path:'.deps/library-mobile.png',fullPage:true});
  let cancelNextCopy=false,resolveCancellation;await page.locator('#closeModal').click();page.on('dialog',async dialog=>{if(cancelNextCopy){cancelNextCopy=false;await dialog.dismiss();resolveCancellation()}else await dialog.accept()});
  const activeToken=await page.evaluate(()=>token),copyResponse=await context.request.post(url+'/api/export',{headers:{Authorization:'Bearer '+activeToken},data:{}});
  assert.equal(copyResponse.ok(),true);const validCopy=await copyResponse.json();
  await page.locator('[data-tab=journal]').click();
  const beforeCancel=await page.evaluate(()=>({version:snapshot.version,state:structuredClone(snapshot.state)})),beforeCancelActions=actions.length,cancelled=new Promise(resolve=>{resolveCancellation=resolve});cancelNextCopy=true;
  const chosenCopy={name:'valid-copy.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(validCopy))};await page.locator('#importFile').setInputFiles(chosenCopy);await cancelled;await page.evaluate(()=>0);assert.equal(await page.locator('#importFile').inputValue(),'');assert.match(await page.locator('#copyImportStatus').textContent(),/Recuperación cancelada.*partida sigue/);assert.equal(actions.length,beforeCancelActions);assert.deepEqual(await page.evaluate(()=>({version:snapshot.version,state:structuredClone(snapshot.state)})),beforeCancel);
  await page.locator('#importFile').setInputFiles(chosenCopy);await page.waitForFunction(v=>snapshot.version>v&&!busy,beforeCancel.version);assert.equal(actions.length,beforeCancelActions+1);
  for(const text of ['{bad json','null','[]']){
   const count=actions.length,version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles({name:'unreadable.json',mimeType:'application/json',buffer:Buffer.from(text)});await page.waitForFunction(()=>!document.querySelector('#copyImportStatus').hidden&&document.querySelector('#copyImportStatus').textContent.includes('No se puede leer'));
   assert.equal(actions.length,count);assert.equal(await page.evaluate(()=>snapshot.version),version);assert.equal(await page.locator('#importFile').inputValue(),'');
  }
  for(const width of [390,1440]){
   await page.setViewportSize({width,height:900});const before=await page.evaluate(()=>({version:snapshot.version,state:structuredClone(snapshot.state)}));
   const damaged=structuredClone(validCopy);damaged.state.board.terrain=[];
   const [rejected]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/action')&&r.status()===400),page.locator('#importFile').setInputFiles({name:'damaged-copy.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(damaged))})]);
   assert.equal(rejected.status(),400);await page.waitForFunction(()=>!busy);assert.match(await page.locator('#toast').textContent(),/partida sigue/);assert.match(await page.locator('#copyImportStatus').textContent(),/Prueba con otra copia/);
   const count=actions.length;await page.locator('#copyImportStatus summary').focus();await page.keyboard.press('Enter');assert.match(await page.locator('#copyImportStatus details').textContent(),/Terreno/);await page.keyboard.press('Enter');assert.equal(actions.length,count);
   assert.deepEqual(await page.evaluate(()=>({version:snapshot.version,state:structuredClone(snapshot.state)})),before);assert.equal(await page.evaluate(()=>localStorage.getItem('cronicas-pending')),null);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));if(width===390)await page.screenshot({path:'.deps/copy-rejected-current-game-mobile.png'});
  }
  if(process.env.TEST_PENDING_REJECTED_REPLAY==='1'){
   const rejected=actions.at(-1),postsBefore=actions.length,before=await page.evaluate(()=>({version:snapshot.version,state:structuredClone(snapshot.state)}));
   await page.evaluate(saved=>{localStorage.setItem('cronicas-pending',JSON.stringify(saved));renderComposerAvailability();renderPlayGuidance(snapshot.state)},{token:await page.evaluate(()=>token),body:rejected});await page.locator('#playGuidanceAction').click();await page.waitForFunction(()=>!busy&&!localStorage.getItem('cronicas-pending'));assert.equal(actions.length,postsBefore,'A previously rejected copy must not be posted again');assert.match(await page.locator('#toast').textContent(),/ya se descartó/);assert.deepEqual(await page.evaluate(()=>({version:snapshot.version,state:structuredClone(snapshot.state)})),before);
  }
  const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles({name:'valid-copy.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(validCopy))});await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
  await page.reload();await page.waitForFunction(()=>snapshot&&!busy);assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hp),originalCharacter.maxHp-5);
  await page.locator('[data-tab=journal]').click();
  await page.evaluate(()=>{const original=File.prototype.text;File.prototype.text=function(){if(this.name!=='slow-copy.json')return original.call(this);const file=this;return new Promise(resolve=>{window.releaseCopyRead=async()=>resolve(await original.call(file))})}});
  await page.locator('#importFile').setInputFiles({name:'slow-copy.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(validCopy))});await page.waitForFunction(()=>typeof window.releaseCopyRead==='function');
  await page.locator('#libraryBtn').click();await page.locator(`#modal [data-library-open="${second.id+':'+second.char.owner}"]:not([data-library-character])`).click();await page.waitForFunction(id=>snapshot.id===id&&!busy,second.id);
  const beforeSwitch=await page.evaluate(()=>({version:snapshot.version,state:structuredClone(snapshot.state)})),count=actions.length;
  await page.evaluate(()=>window.releaseCopyRead());await page.waitForFunction(()=>!busy&&document.querySelector('#toast').textContent.includes('partida ha cambiado'));
  assert.equal(actions.length,count);assert.deepEqual(await page.evaluate(()=>({version:snapshot.version,state:structuredClone(snapshot.state)})),beforeSwitch);assert.equal(await page.locator('#copyImportStatus').isVisible(),false);
  assert.deepEqual(errors,[]);
  console.log('OK: remembers multiple campaigns, copies initial choices with server calculation, original progression preserved, no AI, access backup, pending-action switch protection, reload and mobile.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
