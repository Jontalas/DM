const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],
  {env:{...process.env,TEST_PF_ENCOUNTER_VERSION:'1.5.0',TEST_PF_NIGHT_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  for(const choice of ['parley','combat','armor']){
   const context=await browser.newContext({acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[];
   page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));
   page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');
   await page.locator('#createForm [name=goal]').fill('Resolver la disputa y descansar si lo necesito');await page.locator('#createForm button').click();
   await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();
   await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();
   if(choice==='armor')await page.locator('[data-creator-field=armor]').selectOption('scale');
   await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
   await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();
   await page.waitForFunction(()=>snapshot.state.pfEncounter&&!busy);
   assert.equal(await page.evaluate(()=>snapshot.state.pfEncounter.definition.version),'1.5.0');
   if(choice!=='combat'){
    await page.locator('#pfEncounterParley').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='agreement'&&!busy);
   }else{
    await page.locator('#pfEncounterCombat').click();
    await page.waitForFunction(()=>snapshot.state.board.active&&!document.querySelector('#attackButton').disabled&&!busy);
    assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hp),13);
    await page.locator('#attackButton').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='resolved'&&!busy);
    assert.ok(await page.evaluate(()=>snapshot.state.characters[1].hp<=-snapshot.state.characters[1].abilities[2]));
    await page.locator('[data-tab=story]').click();
   }
   const initial=await page.evaluate(()=>snapshot.state),count=actions.length;
   assert.equal(await page.locator('#pfRestOptions').getAttribute('open'),null);
   await page.locator('#pfRestOptions > summary').focus();await page.keyboard.press('Enter');
   if(choice==='armor'){
    assert.equal(await page.locator('#pfRestNight').isEnabled(),false);
    assert.match(await page.locator('#pfRestHint').textContent(),/armadura.*fatiga/);
    assert.equal(actions.length,count);assert.equal(await page.evaluate(()=>snapshot.state.worldTime),initial.worldTime);
    await page.setViewportSize({width:390,height:1000});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:'.deps/pf-night-armor-mobile.png',fullPage:true});
    await page.locator('#pfContinueScene').click();await page.waitForFunction(()=>snapshot.state.boardScenes?.current==='patio'&&!busy);
    assert.equal(await page.evaluate(()=>snapshot.state.worldTime),initial.worldTime);
    assert.ok(!actions.some(a=>a.type==='rest_pf_night'));assert.deepEqual(errors,[]);
    await context.close();continue;
   }
   assert.equal(await page.locator('#pfRestNight').isEnabled(),true);assert.equal(actions.length,count);
   await page.locator('#pfRestNight').click();await page.waitForFunction(()=>snapshot.state.pfNightRestView?.completed&&!busy);
   const rested=await page.evaluate(()=>snapshot.state),expected=structuredClone(initial.characters);
   expected[0].hp=Math.min(expected[0].maxHp,expected[0].hp+1);
   assert.deepEqual(rested.characters,expected);assert.deepEqual(rested.board,initial.board);
   assert.equal(rested.worldTime,'8 horas desde el comienzo del descanso en el patio');
   assert.equal(actions.length,count+1);assert.equal(actions.at(-1).type,'rest_pf_night');
   assert.equal(await page.locator('#pfRestNight').count(),0);
   assert.match(await page.locator('#pfRestResult').textContent(),choice==='combat'?/recuperado 1 PG/:/recuperado 0 PG/);
   await page.setViewportSize({width:390,height:1000});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:'.deps/pf-night-'+choice+'-mobile.png',fullPage:true});
   await page.locator('[data-tab=journal]').click();
   const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);
   const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());
   await page.waitForFunction(v=>snapshot.version>v&&!busy,version);await page.reload();
   await page.waitForFunction(()=>snapshot?.state.pfNightRestView?.completed);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),rested.characters);
   await page.locator('[data-tab=story]').click();await page.locator('#pfContinueScene').click();
   await page.waitForFunction(()=>snapshot.state.boardScenes?.current==='patio'&&!busy);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),rested.characters.map(c=>c.hp));
   assert.equal(await page.evaluate(()=>snapshot.state.worldTime),rested.worldTime);
   assert.equal(await page.locator('#pfRestNight').count(),0);
   assert.ok(!actions.some(a=>['manual','character','create_npc','start_adventure'].includes(a.type)));
   assert.deepEqual(errors,[]);await context.close();
  }
  console.log('PF night browser verified: guided creation, parley and organic wounded combat, explicit sleep, capped healing, guard unchanged, keyboard help without actions, UI copy/reload/mobile and onward route. No AI.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
