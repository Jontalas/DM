const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const returning=process.env.TEST_PF_ROUTE_RETURN==='1',encounterVersion=returning?'1.6.0':'1.4.0';
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],
  {env:{...process.env,TEST_PF_ENCOUNTER_VERSION:encounterVersion},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  for(const choice of ['parley','combat']){
   const context=await browser.newContext({acceptDownloads:true,hasTouch:true}),page=await context.newPage(),actions=[],errors=[];
   page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));
   page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');
   await page.locator('#createForm [name=goal]').fill('Resolver la disputa y localizar el envío');await page.locator('#createForm button').click();
   await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();
   await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();
   await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
   await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();
   await page.waitForFunction(()=>snapshot.state.pfEncounter&&!busy);
   assert.equal(await page.evaluate(()=>snapshot.state.pfEncounter.definition.version),encounterVersion);
   if(choice==='parley'){
    await page.locator('#pfEncounterParley').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='agreement'&&!busy);
   }else{
    await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!document.querySelector('#attackButton').disabled&&!busy);
    const initiative=page.locator('.initiative-result details'),beforeAudit=actions.length;
    assert.equal(await initiative.evaluate(e=>e.open),false);assert.equal(await page.locator('.npc-preparation details').evaluate(e=>e.open),false);
    const originalInitiative=await page.evaluate(()=>snapshot.state.messages.find(m=>m.kind==='rules'&&m.text.startsWith('Iniciativa d20 + modificador declarado: ')).text);
    await initiative.locator('summary').focus();await page.keyboard.press('Enter');assert.equal(await initiative.evaluate(e=>e.open),true);assert.ok((await initiative.textContent()).includes(originalInitiative));await page.keyboard.press('Enter');assert.equal(await initiative.evaluate(e=>e.open),false);assert.equal(actions.length,beforeAudit);
    await page.setViewportSize({width:390,height:844});await page.locator('[data-tab=board]').tap();assert.equal(await page.locator('#composer').isVisible(),false);assert.equal(await page.locator('#grid .token').first().evaluate(e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight}),true);await page.locator('#toast').waitFor({state:'hidden',timeout:8000});await page.screenshot({path:'.deps/first-combat-mobile.png'});await page.locator('[data-tab=story]').tap();assert.equal(await page.locator('#composer').isVisible(),true);await page.locator('[data-tab=board]').tap();await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:'.deps/first-combat-desktop.png'});
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
   let final=await page.evaluate(()=>snapshot.state);assert.equal(final.adventureRouteView.completed,true);
   if(returning){
    assert.match(await page.locator('#playGuidanceText').textContent(),/Has resuelto el objetivo/);
    const localActions=actions.length;
    await page.locator('#playGuidanceAction').focus();await page.keyboard.press('Enter');
    assert.equal(actions.length,localActions);
    await page.locator('[data-route-exit=patio]').click();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='patio'&&!busy);
    assert.equal(await page.evaluate(()=>snapshot.state.adventureRouteView.completed),true);
    assert.equal(await page.locator('#grid .token').count(),2);
    assert.equal(await page.evaluate(()=>snapshot.state.moduleProgress.discoveries.length),2);
    await page.locator('[data-route-exit=cobertizo]').click();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='cobertizo'&&!busy);
    assert.equal(await page.evaluate(()=>snapshot.state.adventureRouteView.completed),true);
    if(choice==='combat'){
     assert.equal(await page.evaluate(()=>snapshot.state.moduleProgress.completed),false);
     await page.locator('#investigationForm button[value=take10]').click();await page.waitForFunction(()=>snapshot.state.moduleProgress.completed&&!busy);
    }
    await page.locator('[data-route-exit=almacen]').click();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='almacen'&&!busy);
    assert.equal(await page.evaluate(()=>snapshot.state.moduleProgress.discoveries.length),2);
    assert.equal(await page.evaluate(()=>snapshot.state.adventureRouteView.completed),true);
    assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),final.characters);
    final=await page.evaluate(()=>snapshot.state);
   }else{
    assert.match(await page.locator('#playGuidanceText').textContent(),/Has completado la ruta preparada/);
    assert.match(await page.locator('#playGuidanceText').textContent(),/otros viajes aún no están disponibles/);
    assert.equal(await page.locator('[data-route-exit]').count(),0);
   }
   assert.deepEqual(final.characters.map(c=>c.hp),before.characters.map(c=>c.hp));assert.equal(final.characters[1].sceneId,'patio');
   assert.equal(await page.locator('#party [data-character="'+final.characters[1].id+'"]').count(),0);const beforeConsult=actions.length;await page.locator('#otherSceneCharacters').focus();await page.keyboard.press('Enter');
   const npcRow=page.locator(`.party-person[data-character="${final.characters[1].id}"]`);
   if(choice==='combat')assert.match(await npcRow.textContent(),/Ha muerto/);
   else assert.doesNotMatch(await npcRow.textContent(),/Ha muerto|Inconsciente|Moribundo/);
   await npcRow.focus();await page.keyboard.press('Enter');await page.locator('#npcSheetSource').waitFor();await page.locator('#closeModal').click();assert.equal(actions.length,beforeConsult);
   // Render-only defensive cases: never install impossible remote patients in campaign state.
   for(const health of [{hp:-1,stable:false,recoveryState:null,conditions:''},{hp:1,conditions:'Requiere seguimiento'}]){
    await page.evaluate(({id,health})=>renderParty({...snapshot.state,characters:snapshot.state.characters.map(c=>c.id===id?{...c,...health}:c)}),{id:final.characters[1].id,health});assert.equal(await page.locator('#party [data-character="'+final.characters[1].id+'"]').isVisible(),true);
   }
   await page.evaluate(()=>renderParty(snapshot.state));assert.equal(actions.length,beforeConsult);
   assert.equal(final.worldTime,before.worldTime);assert.deepEqual(final.pfEncounter,before.pfEncounter);
   const count=actions.length;
   if(returning)await page.locator('[data-tab=journal]').click();
   else{await page.locator('#playGuidanceAction').focus();await page.keyboard.press('Enter')}
   assert.equal(await page.locator('#journal').isVisible(),true);
   assert.match(await page.locator('#journalOverview').textContent(),/Ruta completada/);
   assert.match(await page.locator('#journalOverview').textContent(),/Hora no registrada/);
   await page.locator('.clock-reference > summary').focus();await page.keyboard.press('Enter');
   assert.match(await page.locator('.clock-reference').textContent(),returning?/Inicio de la noche/:/Comienzo de la aventura/);
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
   await page.screenshot({path:'.deps/pf-route-'+(returning?'return-':'')+choice+'-board-mobile.png',fullPage:true});
   const beforeMobileConsult=actions.length;await page.locator('#otherSceneCharacters').tap();await page.locator('#modalContent [data-character="'+final.characters[1].id+'"]').tap();await page.locator('#npcSheetSource').waitFor();if(choice==='combat'){assert.match(await page.locator('.sheet-checks .notice').textContent(),/Este PNJ ha muerto/);assert.doesNotMatch(await page.locator('.sheet-checks .notice').textContent(),/Tu personaje/)}assert.ok(await page.locator('#modal').evaluate(e=>e.scrollWidth<=e.clientWidth));await page.screenshot({path:'.deps/remote-npc-'+choice+'-mobile.png'});await page.locator('#closeModal').tap();assert.equal(actions.length,beforeMobileConsult);
   await page.locator('[data-tab=journal]').click();await page.locator('.visited-scene-notes > summary').click();
   await page.screenshot({path:'.deps/pf-route-'+(returning?'return-':'')+choice+'-journal-mobile.png',fullPage:true});
   assert.ok(!actions.some(a=>['manual','character','create_npc','start_adventure'].includes(a.type)));
   assert.deepEqual(errors,[]);await context.close();
  }
  console.log('PF route browser passed: guided character, parley/combat, direct/optional route, return preserves clues/positions, guard stays in courtyard, local board filters, journal history, UI copy/reload/mobile. No AI.');
  if(returning)console.log('Global route goal stays resolved on courtyard/shed revisits; optional local investigation remains available, no repeat discoveries or rewards.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
