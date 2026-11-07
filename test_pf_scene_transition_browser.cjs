const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  for(const choice of ['parley','combat']){
   const context=await browser.newContext({acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[];
   page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));
   page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');
   await page.locator('#createForm [name=goal]').fill('Investigar el patio');await page.locator('#createForm button').click();
   await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();
   await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();
   await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
   await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();
   if(choice==='parley'){
    await page.locator('#pfEncounterParley').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='agreement'&&!busy);
   }else{
    await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!busy);
    await page.locator('#attackButton').click();await page.waitForFunction(()=>snapshot.state.characters[1].hp<0&&!busy);
    await page.locator('#pfWaitStabilization').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='resolved'&&!busy);
    assert.ok(await page.evaluate(()=>snapshot.state.characters[1].hp<=-snapshot.state.characters[1].abilities[2]));
   }
   await page.locator('[data-tab=story]').click();
   const before=await page.evaluate(()=>({characters:snapshot.state.characters,board:snapshot.state.board,time:snapshot.state.worldTime,encounter:snapshot.state.pfEncounter}));
   await page.locator('#pfContinueScene').click();await page.waitForFunction(()=>snapshot.state.pfContinuation&&!busy);
   assert.equal(await page.locator('#adventureEntry').isVisible(),false);
   assert.deepEqual(await page.evaluate(()=>({characters:snapshot.state.characters,board:snapshot.state.board,time:snapshot.state.worldTime,encounter:snapshot.state.pfEncounter})),before);
   // Local rendering probe only: no campaign write or invented game outcome.
   const actionsBeforeProbe=actions.length;
   await page.evaluate(()=>{const npc=snapshot.state.characters[1],hp=npc.hp;npc.hp=-3;renderInvestigation();npc.hp=hp;});
   assert.equal(await page.locator('#investigationForm button[value=roll]').isEnabled(),false);
   await page.evaluate(()=>renderInvestigation());assert.equal(actions.length,actionsBeforeProbe);
   for(const method of ['take10','take20']){
    const version=await page.evaluate(()=>snapshot.version);
    await page.locator(`#investigationForm button[value=${method}]`).click();
    await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
   }
   const final=await page.evaluate(()=>snapshot.state);assert.equal(final.adventureModuleView.completed,true);
   assert.match(await page.locator('#playGuidanceText').textContent(),/investigación está resuelta/);
   const beforeJournalGuide=actions.length;await page.locator('#playGuidanceAction').click();
   assert.equal(await page.locator('#journalOverview').isVisible(),true);assert.equal(actions.length,beforeJournalGuide);
   assert.deepEqual(final.characters,before.characters);assert.equal(final.adventureModuleView.discoveries.length,2);
   await page.locator('[data-tab=journal]').click();
   const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);
   const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());
   await page.waitForFunction(v=>snapshot.version>v&&!busy,version);await page.reload();
   await page.waitForFunction(()=>snapshot?.state.adventureModuleView?.completed);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.pfContinuation),final.pfContinuation);
   await page.setViewportSize({width:390,height:1000});await page.locator('[data-tab=story]').click();
   await page.locator('#investigationPanel').scrollIntoViewIfNeeded();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:'.deps/pf-continuation-'+choice+'-mobile.png',fullPage:true});
   assert.equal(actions.filter(a=>a.type==='continue_pf_encounter').length,1);
   assert.ok(!actions.some(a=>['manual','character','start_adventure'].includes(a.type)));
   assert.deepEqual(errors,[]);await context.close();
  }
  console.log('PF continuity browser passed: legal character, parley/combat outcomes, explicit same-patio investigation without state reset, two discoveries, UI copy/reload/mobile. No AI.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
