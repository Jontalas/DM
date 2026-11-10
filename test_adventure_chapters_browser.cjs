const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_ADVENTURE_FIXTURE:'1',TEST_CAMPAIGN_WORLD_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  let context=await browser.newContext({hasTouch:true,acceptDownloads:true}),page=await context.newPage();const actions=[],errors=[];
  const track=page=>{page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept())};track(page);
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Averiguar qué ocurre en la posada');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  await page.locator('#beginAdventure').click();await page.locator('#adventureForm [name=source]').selectOption('example');await page.locator('#adventureForm button').click();await page.waitForFunction(()=>snapshot?.state.adventureModuleView&&!busy);
  for(let search=0;search<2;search++){const version=await page.evaluate(()=>snapshot.version);await page.locator('#investigationForm button[value=take20]').click();await page.waitForFunction(v=>snapshot.version>v&&!busy,version)}
  const first=await page.evaluate(()=>structuredClone(snapshot)),id=first.id,characters=first.state.characters;
  assert.equal(first.state.moduleProgress.completed,true);await page.locator('#exitBtn').click();
  const storage=await context.storageState();await context.close();context=await browser.newContext({storageState:storage,hasTouch:true,acceptDownloads:true});page=await context.newPage();track(page);await page.goto(url);
  await page.locator('#savedCampaigns [data-library-open]:not([data-library-character])').focus();await page.keyboard.press('Enter');await page.waitForFunction(()=>snapshot?.state.moduleProgress.completed&&!busy);assert.equal(await page.evaluate(()=>snapshot.id),id);
  const count=actions.length;await page.locator('#playGuidanceAction').focus();await page.keyboard.press('Enter');await page.locator('#nextAdventureForm').waitFor();assert.equal(actions.length,count);
  const premise='Quiero averiguar quién dejó el sello de la archivera aquí.';await page.locator('#nextAdventureForm [name=premise]').fill(premise);
  const lateDialog=process.env.TEST_CHAPTER_LATE_DIALOG==='1';let sent,release;const sentPromise=new Promise(resolve=>{sent=resolve}),replyGate=new Promise(resolve=>{release=resolve});
  let lost=false;await page.route('**/api/action',async route=>{
   if(route.request().postDataJSON().type==='next_adventure'&&!lost){lost=true;const response=await route.fetch();if(lateDialog){assert.equal(response.status(),200);sent();await replyGate;await route.fulfill({response});return}if(response.status()===200)await route.abort('failed');else await route.fulfill({response})}
   else await route.continue();
  });
  await page.locator('#nextAdventureForm button').click();
  if(lateDialog){
   await sentPromise;await page.locator('#closeModal').click();await page.locator('#libraryBtn').click();release();await page.waitForFunction(()=>snapshot?.state.adventureChaptersView?.current===2&&!busy);await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   assert.equal(await page.locator('#modal').evaluate(e=>e.open),true,'A late chapter reply must preserve the library opened afterward');assert.match(await page.locator('#modalContent h2').textContent(),/Partidas y personajes/);await page.locator('#closeModal').click();await page.locator('[data-tab=story]').click();
  }else{
   await page.waitForFunction(()=>snapshot?.state.adventureChaptersView?.current===2&&!busy&&JSON.parse(localStorage.getItem('cronicas-pending')||'null'));
   assert.equal(await page.locator('#nextAdventureForm [name=premise]').inputValue(),premise);
   const pending=await page.evaluate(()=>JSON.parse(localStorage.getItem('cronicas-pending')));assert.equal(pending.body.premise,premise);assert.equal(pending.body.captureContract,'pf-director-action-1');
   assert.equal(await page.locator('#modal').evaluate(e=>e.open),false);assert.equal(await page.locator('#playGuidance').isVisible(),true);assert.equal(await page.locator('#playGuidance').evaluate(e=>e.parentElement.id),'composer');
   await page.reload();await page.waitForFunction(()=>snapshot?.state.adventureChaptersView?.current===2&&!busy&&!localStorage.getItem('cronicas-pending'));
  }
  const retries=actions.filter(a=>a.type==='next_adventure');assert.equal(retries.length,lateDialog?1:2);if(!lateDialog)assert.deepEqual(retries[0],retries[1]);
  const second=await page.evaluate(()=>structuredClone(snapshot));assert.equal(second.id,id);assert.deepEqual(second.state.characters,characters);assert.equal(second.state.worldTime,first.state.worldTime);
  assert.equal(second.state.moduleProgress.searchActions,0);assert.equal(second.state.adventureModule.premise,premise);assert.equal(second.state.location,first.state.location);
  assert.equal(second.state.messages.filter(m=>m.kind==='director').length,1);assert.equal(second.state.messages.filter(m=>m.kind==='scene'&&m.preparedOpeningSha256).length,1);assert.equal(second.state.messages.filter(m=>m.kind==='action'&&m.text.includes(premise)).length,1);
  await page.locator('[data-tab=journal]').click();assert.match(await page.locator('#journalOverview').textContent(),/Hora no registrada/);assert.equal(await page.locator('#chapterHistory').evaluate(e=>e.open),false);
  const historyCount=actions.length;await page.locator('#chapterHistory > summary').focus();await page.keyboard.press('Enter');assert.equal(actions.length,historyCount);assert.match(await page.locator('#chapterHistoryNotes').textContent(),/carta perdida/i);
  assert.doesNotMatch(await page.locator('#chapterHistoryNotes').textContent(),/PRIVATE/);
  if(process.env.TEST_JOURNAL_READING==='1'){
   const clues=page.locator('#chapterHistoryNotes details').first();await clues.locator('summary').focus();await page.keyboard.press('Enter');const before=await page.evaluate(()=>({state:structuredClone(snapshot.state),version:snapshot.version}));await page.evaluate(()=>{window.keptChapterClues=document.querySelector('#chapterHistoryNotes details');window.journalContentMutations=0;window.journalObserver=new MutationObserver(records=>window.journalContentMutations+=records.length);for(const id of ['journalOverview','chapterHistoryNotes','campaignWorldNotes'])window.journalObserver.observe(document.getElementById(id),{childList:true,characterData:true,subtree:true});render()});const changes=await page.evaluate(()=>{window.journalObserver.disconnect();return window.journalContentMutations});assert.equal(changes,0);assert.equal(await clues.evaluate(e=>e.open),true);assert.equal(await page.evaluate(()=>window.keptChapterClues===document.querySelector('#chapterHistoryNotes details')),true);assert.equal(await clues.locator('summary').evaluate(e=>e===document.activeElement),true);assert.deepEqual(await page.evaluate(()=>({state:structuredClone(snapshot.state),version:snapshot.version})),before);assert.equal(actions.length,historyCount);
  }

  await page.locator('[data-tab=story]').click();for(let search=0;search<2;search++){const version=await page.evaluate(()=>snapshot.version);await page.locator('#investigationForm button[value=take20]').click();await page.waitForFunction(v=>snapshot.version>v&&!busy,version)}
  assert.equal(await page.evaluate(()=>snapshot.state.moduleProgress.completed),true);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),characters);
  await page.locator('[data-tab=journal]').click();const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);const file=await download.path(),exported=JSON.parse(fs.readFileSync(file,'utf8'));
  assert.deepEqual(exported.state.adventureChapters.completed[0].module,first.state.adventureModule);assert.deepEqual(exported.state.adventureChapters.completed[0].progress,first.state.moduleProgress);
  const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(file);await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
  await page.reload();await page.waitForFunction(()=>snapshot?.state.moduleProgress.completed&&!busy);assert.equal(await page.evaluate(()=>snapshot.state.adventureChaptersView.current),2);
  await page.setViewportSize({width:390,height:1000});await page.locator('[data-tab=journal]').tap();await page.locator('#chapterHistory > summary').tap();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/adventure-chapters-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);console.log((lateDialog?'Late reply preserves later library; ':'Lost reply recovered with identical submission; ')+'Two chapters in same campaign: guided creator, complete first investigation, close/rejoin, explicit new goal here, one new simulated response, unchanged ficha/location/clock, historical clues/private originals, copy/reload/keyboard/mobile. Zero real inference.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
