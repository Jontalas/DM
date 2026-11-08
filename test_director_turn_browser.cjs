const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_ADVENTURE_FIXTURE:'1',TEST_DIRECTOR_TURN:'1',TEST_PF_ENCOUNTER_VERSION:'1.10.0',TEST_PF_CEASEFIRE_FIXTURE:'1',TEST_PF_TRUCE_NIGHT:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{createInterface({input:fixture.stdout}).once('line',resolve);fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const page=await browser.newPage({hasTouch:true,acceptDownloads:true}),actions=[],errors=[];page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Resolver el encuentro');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!busy);
  await page.locator('#attackButton').click();await page.waitForFunction(()=>snapshot.state.characters[1].hp===1&&!busy);const before=await page.evaluate(()=>structuredClone(snapshot.state));
  await page.locator('[data-tab=story]').click();await page.locator('#speaker').selectOption(before.characters[0].id);
  const send=async(text,kind)=>{const version=await page.evaluate(()=>snapshot.version);await page.locator('#messageKind').selectOption(kind);await page.locator('#message').fill(text);await page.locator('#send').click();await page.waitForFunction(v=>snapshot.version>v&&!busy,version)};
  await send('¿Debo terminar mi turno?','action');await send('Termino mi turno','dialogue');assert.deepEqual(await page.evaluate(()=>snapshot.state.board),before.board);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),before.characters);
  await page.setViewportSize({width:390,height:1000});await page.locator('#messageKind').selectOption('action');await page.locator('#message').fill('Termino mi turno');const count=actions.length;await page.locator('#message').focus();await page.keyboard.press('Control+Enter');await page.waitForFunction(()=>snapshot.state.board.round===2&&!busy);
  assert.equal(actions.length,count+1);assert.equal(actions.at(-1).type,'talk');assert.equal(actions.at(-1).captureContract,'pf-director-action-1');assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[12,1]);
  assert.equal(await page.evaluate(()=>snapshot.state.board.spent[snapshot.state.characters[0].id].standard||false),false);assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.combat).length),2);
  await page.locator('[data-tab=journal]').tap();const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());await page.waitForFunction(v=>snapshot.version>v&&!busy,version);await page.reload();await page.waitForFunction(()=>snapshot?.state.board.round===2&&!busy);
  assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[12,1]);assert.deepEqual(errors,[]);console.log('Declared turn fixture verified: guided default creator, attack spends standard, question/dialogue keep initiative, keyboard declaration triggers one NPC turn and resets next player budget, mobile/touch/copy/reload. Provider/dice simulated.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
