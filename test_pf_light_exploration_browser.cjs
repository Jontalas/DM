const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const awake=process.env.TEST_AWAKE_EXPLORATION==='1';
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_PF_ENCOUNTER_VERSION:awake?'1.13.0':'1.12.0',TEST_PF_CEASEFIRE_FIXTURE:'1',TEST_PF_TRUCE_NIGHT:'1',TEST_PF_AWAKE_EXPLORATION_FIXTURE:awake?'1':'0'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{createInterface({input:fixture.stdout}).once('line',resolve);fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const page=await browser.newPage({hasTouch:true,acceptDownloads:true}),actions=[],errors=[];page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Investigar conservando mis heridas');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!busy);
  if(!awake){await page.locator('#attackButton').click();await page.waitForFunction(()=>snapshot.state.characters[1].hp===1&&!busy)}
  for(let turn=0;turn<4;turn++){await page.locator('#nextTurn').click();await page.waitForFunction(hp=>snapshot.state.characters[0].hp===hp&&!busy,12-turn*4)}
  if(awake){await page.locator('#attackButton').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.recoveryOutcome?.status==='conscious'&&!busy);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[-1,-2]);await page.locator('[data-tab=story]').click()}
  else{await page.locator('[data-tab=story]').click();await page.locator('#pfAcceptCeasefire').focus();await page.keyboard.press('Enter');await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='agreement'&&!busy)}
  assert.equal(await page.locator('#pfContinueScene').isEnabled(),true);const original=await page.evaluate(()=>structuredClone(snapshot.state.characters));
  const count=actions.length;await page.locator('#pfContinueScene').focus();await page.keyboard.press('Enter');await page.waitForFunction(()=>snapshot.state.boardScenes?.current==='patio'&&!busy);assert.equal(actions.length,count+1);
  assert.match(await page.locator('#investigationPanel').textContent(),/estas búsquedas y caminar sin prisa no cuestan PG/);
  await page.setViewportSize({width:390,height:1000});
  for(const [scene,clues] of [['patio',2],['cobertizo',1],['almacen',2]]){
   if(scene!=='patio'){assert.match(await page.locator(`[data-route-exit=${scene}]`).textContent(),/caminando/);await page.locator(`[data-route-exit=${scene}]`).tap();await page.waitForFunction(s=>snapshot.state.boardScenes.current===s&&!busy,scene)}
   for(let i=0;i<clues;i++){const version=await page.evaluate(()=>snapshot.version);await page.locator('#investigationForm button[value=take20]').tap();await page.waitForFunction(v=>snapshot.version>v&&!busy,version)}
  }
  assert.equal(await page.evaluate(()=>snapshot.state.adventureRouteView.completed),true);await page.locator('[data-route-exit=patio]').tap();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='patio'&&!busy);
  await page.locator('[data-tab=journal]').tap();const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());await page.waitForFunction(v=>snapshot.version>v&&!busy,version);await page.reload();await page.waitForFunction(()=>snapshot?.state.boardScenes?.current==='patio'&&!busy);
  assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(({sceneId,...c})=>c)),original);assert.equal(actions.some(a=>['talk','rest_pf_night','manual'].includes(a.type)),false);assert.deepEqual(errors,[]);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('[data-tab=story]').tap();await page.screenshot({path:awake?'.deps/awake-exploration-mobile.png':'.deps/zero-hp-exploration-mobile.png',fullPage:true});console.log((awake?'Both patients negative/conscious after organic combat/shared recovery':'Zero HP after organic combat/truce')+': legal guided creator, keyboard entry, five clues/three scenes/walking return, unchanged sheets and medical proofs, mobile/touch/copy/reload; zero IA. Dice simulated.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
