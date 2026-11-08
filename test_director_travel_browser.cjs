// Isolated provider fixture; semantic quality of a real model is checked separately.
const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_ADVENTURE_FIXTURE:'1',TEST_DIRECTOR_TRAVEL:'1',TEST_PF_ENCOUNTER_VERSION:'1.9.0'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext({hasTouch:true,acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[];
  page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Localizar el envío');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');
  await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();await page.locator('#pfEncounterParley').click();
  await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='agreement'&&!busy);await page.locator('#pfContinueScene').click();await page.waitForFunction(()=>snapshot.state.boardScenes?.current==='patio'&&!busy);
  for(let i=0;i<2;i++){const version=await page.evaluate(()=>snapshot.version);await page.locator('#investigationForm button[value=take20]').click();await page.waitForFunction(v=>snapshot.version>v&&!busy,version);}
  const before=await page.evaluate(()=>structuredClone(snapshot.state));
  const send=async(text,kind)=>{await page.locator('#messageKind').selectOption(kind);await page.locator('#message').fill(text);const version=await page.evaluate(()=>snapshot.version);await page.locator('#send').click();await page.waitForFunction(v=>snapshot.version>v&&!busy,version);};
  await send('¿Puedo ir al cobertizo?','action');assert.equal(await page.evaluate(()=>snapshot.state.boardScenes.current),'patio');
  await send('Voy al cobertizo','dialogue');assert.equal(await page.evaluate(()=>snapshot.state.boardScenes.current),'patio');
  await page.locator('#messageKind').selectOption('action');await page.locator('#message').fill('Voy al cobertizo');const count=actions.length;
  await page.locator('#message').focus();await page.keyboard.press('Control+Enter');await page.waitForFunction(()=>snapshot.state.boardScenes.current==='cobertizo'&&!busy);
  assert.equal(actions.length,count+1);assert.equal(actions.at(-1).type,'talk');assert.equal(await page.locator('#grid .token').count(),1);
  assert.equal(await page.evaluate(()=>snapshot.state.characters[1].sceneId),'patio');assert.equal(await page.evaluate(()=>snapshot.state.worldTime),before.worldTime);
  await page.setViewportSize({width:390,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('#messageKind').selectOption('action');await page.locator('#message').fill('Vuelvo al patio');await page.locator('#send').tap();await page.waitForFunction(()=>snapshot.state.boardScenes.current==='patio'&&!busy);
  assert.equal(await page.evaluate(()=>snapshot.state.moduleProgress.discoveries.length),2);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[16,7]);
  await page.locator('[data-tab=journal]').click();const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);
  const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
  await page.reload();await page.waitForFunction(()=>snapshot?.state.boardScenes?.current==='patio'&&!busy);assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.routeTransition).length),2);
  await page.screenshot({path:'.deps/director-travel-mobile.png',fullPage:true});assert.deepEqual(errors,[]);
  console.log('Director travel fixture verified: guided creator, questions/dialogue stay put, explicit declaration and keyboard/mobile return use one talk each, guard/health/clues conserved, UI copy/reload. Provider simulated.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
