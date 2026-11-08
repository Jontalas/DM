const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_PF_ENCOUNTER_VERSION:'1.10.0',TEST_PF_CEASEFIRE_FIXTURE:'1',TEST_PF_TRUCE_NIGHT:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  for(const wounded of [false,true]){
   const context=await browser.newContext({hasTouch:true,acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[];
   page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Entender a la guardiana y seguir las pistas');await page.locator('#createForm button').click();
   await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();
   await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
   assert.deepEqual(await page.evaluate(()=>snapshot.state.characters[0].creation.choices.languages),[]);
   await page.locator('#beginPreparedEncounter').click();assert.match(await page.locator('#modalContent').textContent(),/Común/);await page.locator('#pfEncounterEntry button').click();
   await page.waitForFunction(()=>snapshot.state.pfEncounter&&!busy);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[16,6]);
   if(!wounded){await page.locator('#pfEncounterParley').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='agreement'&&!busy);}
   else{
    await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!busy);await page.locator('#attackButton').click();await page.waitForFunction(()=>snapshot.state.characters[1].hp===1&&!busy);
    for(let turn=0;turn<4;turn++){await page.locator('#nextTurn').click();await page.waitForFunction(hp=>snapshot.state.characters[0].hp===hp&&!busy,12-turn*4);}
    await page.locator('[data-tab=story]').click();assert.match(await page.locator('#adventureEntry').textContent(),/en común/);assert.equal(await page.locator('#pfAcceptCeasefire').isEnabled(),true);
    const count=actions.length;await page.locator('#playGuidanceAction').focus();await page.keyboard.press('Enter');assert.equal(actions.length,count);await page.keyboard.press('Enter');await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='agreement'&&!busy);
    assert.equal(await page.evaluate(()=>snapshot.state.pfEncounter.ceasefire.sharedLanguage),'Común');assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[0,1]);
    await page.setViewportSize({width:390,height:1000});await page.locator('#pfRestOptions > summary').tap();await page.locator('#pfRestNight').tap();await page.waitForFunction(()=>snapshot.state.pfNightRestView?.completed&&!busy);
    assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[1,1]);assert.equal(await page.evaluate(()=>snapshot.state.pfNightRestView.result.seconds),28800);
   }
   await page.locator('[data-tab=journal]').click();const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);
   const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());await page.waitForFunction(v=>snapshot.version>v&&!busy,version);await page.reload();await page.waitForFunction(()=>snapshot?.state.pfEncounter.phase==='agreement'&&!busy);
   await page.locator('[data-tab=story]').click();await page.locator('#pfContinueScene').click();await page.waitForFunction(()=>snapshot.state.boardScenes?.current==='patio'&&!busy);
   for(let clue=0;clue<2;clue++){const version=await page.evaluate(()=>snapshot.version);await page.locator('#investigationForm button[value=take20]').click();await page.waitForFunction(v=>snapshot.version>v&&!busy,version);}
   await page.locator('[data-route-exit=cobertizo]').click();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='cobertizo'&&!busy);
   assert.equal(await page.evaluate(()=>snapshot.state.characters[1].sceneId),'patio');assert.equal(await page.evaluate(()=>snapshot.state.characters[1].maxHp),6);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.characters[0].creation.choices.languages),[]);assert.equal(actions.filter(a=>a.type==='manual').length,0);
   await page.setViewportSize({width:390,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/common-guard-'+(wounded?'truce':'peace')+'-mobile.png',fullPage:true});
   assert.deepEqual(errors,[]);await context.close();
  }
  console.log('Common guard verified: default guided creator with no extra language, legal new6HP variant, peace and organic zero/truce/night, common offer, keyboard/mobile/touch/UI copy/reload, clues/route/guard retained; no provider.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
