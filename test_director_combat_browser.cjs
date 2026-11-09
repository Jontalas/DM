const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_ADVENTURE_FIXTURE:'1',TEST_DIRECTOR_MELEE:'1',TEST_PF_ENCOUNTER_VERSION:'1.9.0',TEST_PF_CEASEFIRE_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext({hasTouch:true,acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[];
  page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Resolver el paso');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();
  await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!busy);
  await page.locator('[data-tab=story]').click();
  const send=async(text,kind,keyboard=false)=>{const version=await page.evaluate(()=>snapshot.version),count=actions.length;await page.locator('#messageKind').selectOption(kind);await page.locator('#message').fill(text);if(keyboard){await page.locator('#message').focus();await page.keyboard.press('Control+Enter')}else await page.locator('#send').tap();await page.waitForFunction(v=>snapshot.version>v&&!busy,version);assert.equal(actions.length,count+1);assert.equal(actions.at(-1).type,'talk');};
  await send('¿Puedo atacar a la guardiana?','action');assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[16,7]);
  await send('Ataco a la guardiana con mi espada','dialogue');assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[16,7]);
  await send('Ataco a la guardiana con mi espada','action',true);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[16,2]);
  assert.equal(await page.evaluate(()=>snapshot.state.board.spent[snapshot.state.characters[0].id].standard),true);assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.combat).length),1);
  assert.equal(await page.locator('#attackButton').isEnabled(),false);assert.equal(actions.filter(a=>a.type==='attack').length,0);
  assert.match(await page.locator('.combat-result').textContent(),/Impacto.*Aria.*Guardiana del patio/);assert.match(await page.locator('.combat-result').textContent(),/Daño: 5.*2 PG/);assert.equal(await page.locator('.combat-audit').evaluate(e=>e.open),false);
  await page.setViewportSize({width:390,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('.combat-result').scrollIntoViewIfNeeded();await page.screenshot({path:'.deps/attack-result-mobile.png'});
  await send('Ataco a la guardiana con mi espada','action');assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[16,2]);assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.combat).length),1);
  await page.locator('[data-tab=journal]').click();const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);
  const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());await page.waitForFunction(v=>snapshot.version>v&&!busy,version);await page.reload();await page.waitForFunction(()=>snapshot?.state.board.active&&!busy);
  assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[16,2]);assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.combat).length),1);
  await page.screenshot({path:'.deps/declared-melee-mobile.png',fullPage:true});assert.deepEqual(errors,[]);
  console.log('Declared melee fixture verified: guided creator, question/dialogue do not attack, keyboard declaration resolves same engine damage, spent standard blocks repeat, mobile/touch/UI copy/reload. Provider/dice simulated; durable real server dice tested in HTTP.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
