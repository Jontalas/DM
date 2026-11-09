const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const encounterVersion=process.env.TEST_PF_ENCOUNTER_VERSION||'1.9.0';
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_ADVENTURE_FIXTURE:'1',TEST_DIRECTOR_PREPARED_DECISIONS:'1',TEST_PF_ENCOUNTER_VERSION:encounterVersion,TEST_PF_CEASEFIRE_FIXTURE:'1',TEST_PF_TRUCE_NIGHT:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  for(const scale of [false,true]){
   const context=await browser.newContext({hasTouch:true,acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[];
   page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Resolver el paso');await page.locator('#createForm button').click();await page.waitForFunction(()=>snapshot?.state&&!busy);
   // Legal character builder input; no manually edited health or statistics.
   await page.evaluate(async scale=>{await act('create_character',{choices:{name:'Aria',race:'human',class:'fighter',level:1,abilities:[16,14,14,12,10,8],bonus:0,weapon:'longsword',armor:scale?'scale':'chainshirt',shield:'heavy',favored:'hp',feats:['focus','initiative','toughness'],skills:['climb','intimidate','perception','swim'],languages:['Goblin']}})},scale);
   await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!busy);
   const remainingNpcHp=await page.evaluate(()=>snapshot.state.characters[1].hp-5);
   assert.equal(await page.evaluate(()=>snapshot.state.pfEncounter.definition.version),encounterVersion);
   await page.locator('#attackButton').click();await page.waitForFunction(hp=>snapshot.state.characters[1].hp===hp&&!busy,remainingNpcHp);
   if(!scale){for(let turn=0;turn<4;turn++){await page.locator('#nextTurn').click();await page.waitForFunction(hp=>snapshot.state.characters[0].hp===hp&&!busy,12-turn*4);}}
   await page.locator('[data-tab=story]').click();await page.locator('#messageKind').selectOption('action');
   const send=async(text,keyboard=false)=>{const version=await page.evaluate(()=>snapshot.version),count=actions.length;await page.locator('#message').fill(text);if(keyboard){await page.locator('#message').focus();await page.keyboard.press('Control+Enter')}else await page.locator('#send').tap();await page.waitForFunction(v=>snapshot.version>v&&!busy,version);assert.equal(actions.length,count+1);assert.equal(actions.at(-1).type,'talk');};
   const hp=scale?16:0;await send('¿Puedo aceptar la tregua?');assert.equal(await page.evaluate(()=>snapshot.state.board.active),true);
   await send('Acepto la tregua',true);assert.equal(await page.evaluate(()=>snapshot.state.board.active),false);assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hp),hp);
   await send('Quiero descansar');assert.equal(await page.evaluate(()=>snapshot.state.pfNightRestView.completed),false);
   await page.setViewportSize({width:390,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await send(scale?'Me quito la cota, duermo sin ella y vuelvo a equiparla.':'Duermo8h con mi armadura ligera');
   assert.equal(await page.evaluate(()=>snapshot.state.pfNightRestView.completed),true);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[scale?16:1,remainingNpcHp]);
   assert.equal(await page.evaluate(()=>snapshot.state.pfNightRestView.result.seconds),scale?29100:28800);assert.equal(await page.evaluate(()=>!!snapshot.state.pfContinuation),false);
   await send('Empiezo a investigar el registro del patio');assert.equal(await page.evaluate(()=>snapshot.state.boardScenes.current),'patio');
   await page.locator('[data-tab=journal]').click();const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);
   const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());await page.waitForFunction(v=>snapshot.version>v&&!busy,version);await page.reload();await page.waitForFunction(()=>snapshot?.state.pfNightRestView?.completed&&!busy);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[scale?16:1,remainingNpcHp]);assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.nightRestSha256).length),1);
   await page.screenshot({path:'.deps/declared-prepared-'+(scale?'scale':'zero')+'-mobile.png',fullPage:true});assert.deepEqual(errors,[]);await context.close();
  }
  console.log('Prepared declaration fixture verified: legal builder API, organic wounds/zero HP, question/ambiguous rest do not act, separate truce/sleep/investigation, explicit scale plan, keyboard/mobile/touch, UI copy/reload; provider simulated.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
