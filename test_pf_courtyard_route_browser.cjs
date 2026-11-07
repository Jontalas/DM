const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],
  {env:{...process.env,TEST_PF_ENCOUNTER_VERSION:'1.4.0'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  for(const choice of ['parley','combat']){
   const context=await browser.newContext({acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[];
   page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));
   page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');
   await page.locator('#createForm [name=goal]').fill('Resolver la disputa y localizar el envío');await page.locator('#createForm button').click();
   await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();
   await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();
   await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
   await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();
   await page.waitForFunction(()=>snapshot.state.pfEncounter&&!busy);
   assert.equal(await page.evaluate(()=>snapshot.state.pfEncounter.definition.version),'1.4.0');
   if(choice==='parley'){
    await page.locator('#pfEncounterParley').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='agreement'&&!busy);
   }else{
    await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!document.querySelector('#attackButton').disabled&&!busy);
    await page.locator('#attackButton').click();await page.waitForFunction(()=>snapshot.state.characters[1].hp<0&&!busy);
    await page.locator('#pfWaitStabilization').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='resolved'&&!busy);
   }
   await page.locator('[data-tab=story]').click();
   const before=await page.evaluate(()=>snapshot.state);await page.locator('#pfContinueScene').click();
   await page.waitForFunction(()=>snapshot.state.boardScenes?.current==='patio'&&!busy);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),before.characters.map(c=>c.hp));
   for(const method of ['take10','take20']){
    const version=await page.evaluate(()=>snapshot.version);await page.locator(`#investigationForm button[value=${method}]`).click();
    await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
   }
   assert.equal(await page.locator('#playGuidanceAction').textContent(),'Ver salidas');
   if(choice==='parley'){
    await page.locator('#grid [data-x="0"][data-y="1"]').click();await page.locator('#confirmMove').click();
    await page.waitForFunction(()=>snapshot.state.characters[0].y===1&&!busy);
    await page.locator('[data-route-exit=cobertizo]').click();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='cobertizo'&&!busy);
    assert.equal(await page.locator('#grid .token').count(),1);
    assert.equal(await page.locator('#boardCharacter option').count(),1);
    assert.equal(await page.locator('#attackTarget option').count(),0);
    assert.match(await page.locator('#party').textContent(),/En otra escena/);
    assert.equal(await page.evaluate(()=>snapshot.state.characters[1].sceneId),'patio');
    await page.locator('#investigationForm button[value=take10]').click();await page.waitForFunction(()=>snapshot.state.moduleProgress.completed&&!busy);
    await page.locator('[data-route-exit=patio]').click();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='patio'&&!busy);
    assert.equal(await page.evaluate(()=>snapshot.state.characters[0].y),1);assert.equal(await page.locator('#grid .token').count(),2);
    assert.equal(await page.evaluate(()=>snapshot.state.moduleProgress.discoveries.length),2);
   }
   await page.locator('[data-route-exit=almacen]').click();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='almacen'&&!busy);
   assert.equal(await page.locator('#grid .token').count(),1);assert.equal(await page.locator('#startCombat').isEnabled(),false);
   for(const method of ['take10','take20']){
    const version=await page.evaluate(()=>snapshot.version);await page.locator(`#investigationForm button[value=${method}]`).click();
    await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
   }
   const final=await page.evaluate(()=>snapshot.state);assert.equal(final.adventureRouteView.completed,true);
   assert.deepEqual(final.characters.map(c=>c.hp),before.characters.map(c=>c.hp));assert.equal(final.characters[1].sceneId,'patio');
   assert.equal(final.worldTime,before.worldTime);assert.deepEqual(final.pfEncounter,before.pfEncounter);
   await page.locator('[data-tab=journal]').click();const count=actions.length;
   assert.match(await page.locator('#journalOverview').textContent(),/Ruta completada/);
   assert.match(await page.locator('#journalOverview').textContent(),/Hora no registrada/);
   await page.locator('.visited-scene-notes > summary').focus();await page.keyboard.press('Enter');
   assert.match(await page.locator('.visited-scene-notes').textContent(),/última línea|último envío|mismo sello/);
   assert.equal(actions.length,count);
   const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);
   const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());
   await page.waitForFunction(v=>snapshot.version>v&&!busy,version);await page.reload();
   await page.waitForFunction(()=>snapshot?.state.adventureRouteView?.completed);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.boardScenes),final.boardScenes);
   await page.setViewportSize({width:390,height:1000});await page.locator('[data-tab=board]').click();
   assert.match(await page.locator('#board h2').textContent(),/Almacén/);assert.equal(await page.locator('#grid .token').count(),1);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:'.deps/pf-route-'+choice+'-board-mobile.png',fullPage:true});
   await page.locator('[data-tab=journal]').click();await page.locator('.visited-scene-notes > summary').click();
   await page.screenshot({path:'.deps/pf-route-'+choice+'-journal-mobile.png',fullPage:true});
   assert.ok(!actions.some(a=>['manual','character','create_npc','start_adventure'].includes(a.type)));
   assert.deepEqual(errors,[]);await context.close();
  }
  console.log('PF route browser passed: guided character, parley/combat, direct/optional route, return preserves clues/positions, guard stays in courtyard, local board filters, journal history, UI copy/reload/mobile. No AI.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
