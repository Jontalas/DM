const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const declared=process.env.TEST_DECLARED_NPC_WAIT==='1';
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_ADVENTURE_FIXTURE:declared?'1':'0',TEST_DIRECTOR_NPC_WAIT:declared?'1':'0',TEST_PF_ENCOUNTER_VERSION:'1.11.0',TEST_PF_NPC_WAIT_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{createInterface({input:fixture.stdout}).once('line',resolve);fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const page=await browser.newPage({hasTouch:true,acceptDownloads:true}),actions=[],errors=[];page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Seguir las pistas después del combate');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!busy);
  await page.locator('#attackButton').click();await page.waitForFunction(()=>snapshot.state.characters[1].hp===-2&&!busy);await page.locator('#nextTurn').click();await page.waitForFunction(()=>snapshot.state.board.round===2&&!busy);
  await page.locator('[data-tab=story]').click();await page.locator('#pfFirstAidForm button').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='resolved'&&!busy);
  assert.equal(await page.locator('#pfContinueScene').isEnabled(),false);const before=await page.evaluate(()=>structuredClone(snapshot.state));assert.deepEqual(before.characters.map(c=>c.hp),[16,-3]);
  if(declared){
   await page.locator('#speaker').selectOption(before.characters[0].id);
   for(const [text,kind] of [['¿Espero a que despierte?','action'],['Espero junto a la guardiana a que despierte','dialogue']]){const version=await page.evaluate(()=>snapshot.version);await page.locator('#messageKind').selectOption(kind);await page.locator('#message').fill(text);await page.locator('#send').click();await page.waitForFunction(v=>snapshot.version>v&&!busy,version)}
   assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),before.characters);assert.deepEqual(await page.evaluate(()=>snapshot.state.board),before.board);
  }
  const count=actions.length;
  if(declared){await page.locator('#messageKind').selectOption('action');await page.locator('#message').fill('Espero junto a la guardiana a que despierte');await page.locator('#message').focus();await page.keyboard.press('Control+Enter')}
  else{await page.locator('#pfWaitNpcRecovery').focus();await page.keyboard.press('Enter')}
  await page.waitForFunction(()=>snapshot.state.pfNpcRecoveryView?.canContinue&&!busy);
  assert.equal(actions.length,count+1);assert.equal(actions.at(-1).type,declared?'talk':'wait_pf_npc_recovery');assert.deepEqual(await page.evaluate(()=>snapshot.state.characters[0]),before.characters[0]);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[16,-3]);
  assert.match(await page.locator('#adventureEntry').textContent(),/ha despertado/);assert.equal(await page.locator('#pfContinueScene').isEnabled(),true);assert.equal(await page.locator('#pfRestNight').isEnabled(),false);
  await page.setViewportSize({width:390,height:1000});await page.locator('#pfContinueScene').tap();await page.waitForFunction(()=>snapshot.state.boardScenes?.current==='patio'&&!busy);
  if(declared){
   const version=await page.evaluate(()=>snapshot.version);await page.locator('#message').fill('Examino el registro del patio');await page.locator('#send').tap();await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
   assert.equal(await page.locator('[data-resolve-check]').evaluateAll(bs=>bs.every(b=>!b.disabled)),true);await page.locator('.primary[data-resolve-check]').tap();await page.waitForFunction(()=>snapshot.state.moduleProgress.discoveries.length===1&&!busy);
  }
  for(let i=declared?1:0;i<2;i++){const version=await page.evaluate(()=>snapshot.version);await page.locator('#investigationForm button[value=take20]').tap();await page.waitForFunction(v=>snapshot.version>v&&!busy,version)}
  await page.locator('[data-route-exit=cobertizo]').tap();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='cobertizo'&&!busy);assert.equal(await page.locator('#grid .token').count(),1);
  const next=await page.evaluate(()=>snapshot.version);await page.locator('#investigationForm button[value=take20]').tap();await page.waitForFunction(v=>snapshot.version>v&&!busy,next);
  await page.locator('[data-route-exit=almacen]').tap();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='almacen'&&!busy);
  for(let i=0;i<2;i++){const version=await page.evaluate(()=>snapshot.version);await page.locator('#investigationForm button[value=take20]').tap();await page.waitForFunction(v=>snapshot.version>v&&!busy,version)}
  assert.equal(await page.evaluate(()=>snapshot.state.adventureRouteView.completed),true);
  assert.equal(await page.locator('#continueAdventure').textContent(),'Pedir narración al director');assert.equal(await page.locator('#continueAdventure').evaluate(b=>b.classList.contains('primary')),false);
  assert.match(await page.locator('#continueAdventureHint').textContent(),declared?/Opcional.*tiradas ya están resueltas/:/Puedes seguir con las opciones/);
  await page.locator('[data-route-exit=patio]').tap();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='patio'&&!busy);assert.equal(await page.locator('#grid .token').count(),2);
  await page.locator('[data-tab=journal]').tap();const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());await page.waitForFunction(v=>snapshot.version>v&&!busy,version);await page.reload();await page.waitForFunction(()=>snapshot?.state.boardScenes?.current==='patio'&&!busy);
  assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[16,-3]);assert.equal(await page.evaluate(()=>snapshot.state.pfEncounter.npcRecovery.hours),2);assert.equal(actions.some(a=>a.type==='manual'),false);assert.equal(actions.filter(a=>a.type==='talk').length,declared?4:0);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
  await page.screenshot({path:'.deps/npc-wait-route-mobile.png',fullPage:true});console.log('NPC wait verified: guided creator, organic attack/stabilization/first aid, owner keyboard wait without healing, one action for two hourly checks, negative conscious guard remains, five clues/three scenes/return, mobile/touch/copy/reload. '+(declared?'Declaration, question/dialogue guards and provider simulated.':'Zero AI.')+' Dice simulated.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
