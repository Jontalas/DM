const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_CAIRN_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),token=(await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Experimental Cairn fixture',ruleset:'cairn-1e'}})).json()).token;
  await context.addInitScript(t=>{if(!localStorage.getItem('cronicas-token'))localStorage.setItem('cronicas-token',t)},token);
  const page=await context.newPage(),actions=[],errors=[],resources=[];
  page.on('pageerror',error=>errors.push(error.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON());if(r.url().includes('/api/system-resources'))resources.push(r.url())});
  await page.goto(url);await page.locator('#cairnBegin').waitFor();
  assert.ok(await page.locator('#app > .workspace').isHidden());
  await page.locator('#cairnBegin button').click();await page.locator('#cairnBonus').waitFor();
  const original=await page.evaluate(()=>snapshot.state.creationDrafts[snapshot.me.id]);
  assert.equal(actions.length,1);
  await page.locator('#cairnBonus [name=table]').selectOption('trinkets');
  await page.locator('#cairnBonus button').click();await page.locator('#cairnBonus').waitFor({state:'detached'});
  await page.locator('[data-weapon-group=weapons]').selectOption('Dagger');
  const version=await page.evaluate(()=>snapshot.version),count=resources.length;
  await page.locator('#cairnReview [name=name]').selectOption('20');
  await page.locator('#cairnReview [name=background]').selectOption('20');
  await page.locator('#cairnReview [name=swap]').selectOption('STR,WIL');
  await page.locator('[data-item-state=torch]').selectOption('stored');
  assert.equal(actions.length,2);assert.equal(resources.length,count);
  assert.equal(await page.evaluate(()=>snapshot.version),version);
  assert.match(await page.locator('#cairnPreviewStatus').textContent(),/Puedes guardar/);
  assert.ok(!(await page.locator('#systemWorkspace').textContent()).includes('Guerrero'));
  assert.ok(await page.locator('#cairnConfirm').isEnabled());
  await page.reload();await page.locator('#cairnReview').waitFor();
  assert.equal(await page.locator('#cairnReview [name=name]').inputValue(),'20');
  assert.equal(await page.locator('[data-weapon-group=weapons]').inputValue(),'Dagger');
  assert.equal(await page.locator('[data-item-state=torch]').inputValue(),'stored');
  const restored=await page.evaluate(()=>snapshot.state.creationDrafts[snapshot.me.id]);
  assert.deepEqual(restored.core,original.core);assert.equal(restored.bonus.table,'trinkets');
  assert.equal(actions.length,2);
  await page.setViewportSize({width:390,height:844});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:'.deps/cairn-creator-mobile.png',fullPage:true});
  let lost=false;
  await page.route('**/api/action',async route=>{
   if(!lost&&route.request().postDataJSON()?.type==='confirm_character'){lost=true;await route.fetch();await route.abort('connectionfailed')}
   else await route.continue();
  });
  await page.locator('#cairnConfirm').click();
  await page.waitForFunction(()=>snapshot.state.characters.length===1&&localStorage.getItem('cronicas-pending'));
  const pending=await page.evaluate(()=>JSON.parse(localStorage.getItem('cronicas-pending')));
  await page.reload();await page.locator('[data-cairn-character]').waitFor();
  assert.equal(await page.evaluate(()=>snapshot.state.characters.length),1);
  assert.equal(await page.evaluate(()=>localStorage.getItem('cronicas-pending')),null);
  assert.equal(actions.at(-1).id,pending.body.id);
  const confirmed=await page.evaluate(()=>snapshot.state.characters[0]);
  assert.deepEqual(confirmed.creation.draft.core,original.core);assert.equal(confirmed.creation.complete,true);
  assert.ok(await page.locator('#cairnBegin').isHidden());
  await page.locator('[data-cairn-character]').click();await page.locator('#modal').waitFor({state:'visible'});
  assert.match(await page.locator('#modalContent').textContent(),/Yslen Abernathy/);
  assert.match(await page.locator('#modalContent').textContent(),/Origen de los cálculos/);
  await page.locator('#closeModal').click();
  const entry=await page.evaluate(()=>CampaignLibrary.read(localStorage).entries.find(e=>e.ruleset==='cairn-1e'));
  assert.equal(entry.characters.length,1);assert.equal(entry.characters[0].background,'Ranger');
  assert.ok(!('level' in entry.characters[0]));
  await page.screenshot({path:'.deps/cairn-character-mobile.png',fullPage:true});
  await page.locator('#exitBtn').click();
  await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Volver a Pathfinder');
  await page.locator('#createForm button').click();await page.locator('#app > .workspace').waitFor({state:'visible'});
  assert.ok(await page.locator('#systemWorkspace').isHidden());
  assert.match(await page.locator('#campaignMeta').textContent(),/Pathfinder 1e/);
  if(process.env.TEST_MESSAGE_HISTORY_SCOPE==='1'){
   await page.evaluate(()=>{window.pfHistoryIntro=document.querySelector('#messages [data-create-hero]')});await page.locator('#messageKind').selectOption('private');await page.locator('#message').fill('Nota privada de la partida Pathfinder.');await page.locator('#send').click();await page.waitForFunction(()=>!busy&&snapshot.state.messages.some(m=>m.kind==='private'));assert.equal(await page.locator('#messages [data-create-hero]').count(),1);assert.equal(await page.evaluate(()=>window.pfHistoryIntro===document.querySelector('#messages [data-create-hero]')),true);await page.evaluate(()=>{window.pfPrivateHistory=document.querySelector('#messages .private')});assert.equal(await page.locator('#messages .private').count(),1);
  }

  await page.locator('#libraryBtn').click();
  await page.locator(`#modal [data-library-entry="${entry.id}"] .library-characters>summary`).click();await page.locator(`#modal [data-library-open="${entry.id}"][data-library-character="${confirmed.id}"]`).click();
  await page.waitForFunction(id=>snapshot.id===id,entry.campaign);
  await page.locator('#modal').waitFor({state:'visible'});
  assert.equal(await page.locator('#modalContent > h2').textContent(),'Yslen Abernathy');
  assert.match(await page.locator('#campaignMeta').textContent(),/Cairn 1e/);
  if(process.env.TEST_MESSAGE_HISTORY_SCOPE==='1'){assert.equal(await page.locator('#messages > *').count(),0);assert.equal(await page.evaluate(()=>window.pfPrivateHistory.isConnected),false);assert.equal(await page.evaluate(()=>window.pfHistoryIntro.isConnected),false);for(const id of ['journalOverview','campaignWorldNotes','chapterHistoryNotes'])assert.equal(await page.locator('#'+id+' > *').count(),0)}
  await page.locator('#closeModal').click();
  const beforeScene=actions.length;
  await page.locator('#startCairnAdventure').click();
  await page.locator('[data-cairn-route=pasarela]').waitFor();
  await page.locator('[data-cairn-route=pasarela]').click();await page.locator('#cairnSave').waitFor();
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].abilities.DEX),3);
  await page.locator('#cairnSave [name=physical]').fill('20');
  await page.evaluate(()=>refresh(true)); // A shared-state refresh must preserve a physical die being entered.
  assert.equal(await page.locator('#cairnSave [name=physical]').inputValue(),'20');
  await page.locator('#cairnSave button').click();
  await page.waitForFunction(()=>snapshot.state.characters[0].abilities.DEX===2);
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hitProtection),1);
  assert.equal(await page.evaluate(()=>snapshot.state.adventureView.completed),false);
  await page.locator('#cairnRest').click();
  await page.waitForFunction(()=>snapshot.state.adventureView.elapsedDays===7);
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].abilities.DEX),3);
  await page.locator('[data-cairn-route=sendero]').click();
  await page.waitForFunction(()=>snapshot.state.adventureView.completed);
  assert.deepEqual(actions.slice(beforeScene).map(a=>a.type),['start_cairn_adventure','choose_route','resolve_save','rest_and_recover','choose_route']);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:'.deps/cairn-scene-mobile.png',fullPage:true});
  // A slow local catalog must not reopen the workspace after the player exits.
  const slowContext=await browser.newContext();await slowContext.addInitScript(t=>localStorage.setItem('cronicas-token',t),token);
  const slowPage=await slowContext.newPage();slowPage.on('pageerror',error=>errors.push(error.message));
  let release;const gate=new Promise(resolve=>release=resolve);
  await slowPage.route('**/api/system-resources**',async route=>{await gate;await route.continue()});
  await slowPage.goto(url);await slowPage.locator('#app').waitFor({state:'visible'});
  await slowPage.locator('#exitBtn').click();await slowPage.locator('#welcome').waitFor({state:'visible'});
  const received=slowPage.waitForResponse(r=>r.url().includes('/api/system-resources'));
  release();await (await received).finished();
  await slowPage.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  assert.ok(await slowPage.locator('#app').isHidden());assert.ok(await slowPage.locator('#welcome').isVisible());
  await slowContext.close();
  assert.deepEqual(errors,[]);
  console.log('OK: Cairn creation, lost-response recovery, classless library, native save/injury/week rest/safe completion, physical input preservation, mobile and system switching. Experimental fixture only.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
