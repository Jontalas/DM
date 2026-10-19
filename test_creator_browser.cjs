const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process');const {createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const host=await browser.newContext(),guest=await browser.newContext();
  const token=(await (await host.request.post(url+'/api/create',{data:{player:'Ana',title:'Creation'}})).json()).token;
  const headers={Authorization:'Bearer '+token};const room=await (await host.request.get(url+'/api/state',{headers})).json();
  const player=(await (await guest.request.post(url+'/api/join',{data:{name:'Luis',invite:room.invite}})).json()).token;
  await host.addInitScript(t=>localStorage.setItem('cronicas-token',t),token);await guest.addInitScript(t=>localStorage.setItem('cronicas-token',t),player);
  const a=await host.newPage(),b=await guest.newPage(),errors=[],actions=[];
  for(const page of [a,b])page.on('pageerror',e=>errors.push(e.message));
  b.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await b.goto(url);await b.locator('#app').waitFor({state:'visible'});
  await b.locator('[data-create-hero]').click();await b.locator('#creatorForm').waitFor();
  assert.equal(await b.locator('#creatorEnemy').count(),0);
  await b.locator('[data-creator-preset=vanguard]').click();await b.locator('#creatorName').fill('Aria');
  await b.locator('#creatorNext').click();await b.locator('[data-creator-ability="0"]').fill('18');
  assert.match(await b.locator('#creatorErrors').textContent(),/20 puntos/);
  await b.locator('[data-creator-ability="0"]').fill('16');await b.locator('#creatorNext').click();
  assert.equal(await b.locator('#creatorRanks').textContent(),'3 / 3 rangos asignados · 3 / 3 dotes · 0 / 0 idiomas adicionales');
  await b.locator('#creatorNext').click();assert.match(await b.locator('#creatorPreview').textContent(),/2d6\+6/);
  assert.equal(actions.length,0);await b.locator('#creatorFinish').click();await b.locator('.sheet-checks').waitFor();
  assert.equal(actions.length,1);assert.equal(actions[0].type,'create_character');assert.equal(await b.locator('#characterForm').count(),0);
  let state=await (await guest.request.get(url+'/api/state',{headers:{Authorization:'Bearer '+player}})).json();
  const character=state.state.characters[0];assert.equal(character.damage,'2d6+6');assert.equal(character.ac,16);assert.equal(character.maxHp,16);assert.ok(character.creation);
  await b.locator('[data-check-key=str]').click();await b.waitForFunction(()=>snapshot.state.messages.at(-1).check?.total===16);
  await b.locator('#closeModal').click();await b.reload();await b.locator('.party-person').click();await b.locator('.sheet-checks').waitFor();
  assert.equal(await b.locator('#advancedCharacterEdit').count(),1);await b.locator('#closeModal').click();
  // A host can create a usable opposing fighter through the same wizard.
  await a.goto(url);await a.locator('#app').waitFor({state:'visible'});await a.locator('#addCharacter').click();
  await a.locator('#creatorName').fill('Bandido');await a.locator('#creatorEnemy').check();
  await a.setViewportSize({width:390,height:844});
  for(let step=0;step<4;step++){
   await a.locator(`[data-creator-step="${step}"]`).click();
   assert.equal(await a.locator('#modal').evaluate(el=>el.scrollWidth<=el.clientWidth),true);
  }
  await a.screenshot({path:'.deps/creator-mobile.png',fullPage:true});
  await a.locator('#creatorFinish').click();await a.locator('.sheet-checks').waitFor();await a.locator('#closeModal').click();
  await a.setViewportSize({width:1440,height:1000});await a.locator('#startCombat').click();await a.waitForFunction(()=>snapshot.state.board.active);
  await b.reload();await b.locator('#app').waitFor({state:'visible'});
  await b.waitForFunction(()=>!document.querySelector('#attackButton').disabled);
  await b.locator('#attackButton').click();await b.waitForFunction(()=>snapshot.state.board.spent[snapshot.state.characters[0].id]?.standard);
  state=await (await guest.request.get(url+'/api/state',{headers:{Authorization:'Bearer '+player}})).json();
  assert.ok(state.state.characters[1].hp<state.state.characters[1].maxHp);
  assert.deepEqual(errors,[]);console.log('OK: zero manual statistics; guided creation, local invalid-budget preview, one save, sheet roll, reload, mobile wizard, generated adversary and real engine attack. No AI.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
