// Local two-player UI test. Requires Playwright under .deps/browser-tests.
const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process');
const {createInterface}=require('node:readline');
const path=require('node:path');
const assert=require('node:assert/strict');

(async()=>{
 const python=process.env.TEST_PYTHON||path.resolve('.venv/Scripts/python.exe');
 const fixture=spawn(python,['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});
 let browser;
 try{
  const url=await new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>reject(Error('Fixture startup timed out')),15000);
   fixture.once('exit',code=>{clearTimeout(timer);reject(Error('Fixture exited: '+code))});
   createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});
  });
  browser=await chromium.launch({headless:true,executablePath:process.env.TEST_BROWSER||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const host=await browser.newContext(),guest=await browser.newContext();
  const a=await host.newPage(),b=await guest.newPage(),errors=[];
  for(const page of [a,b])page.on('pageerror',error=>errors.push(error.message));
  await a.goto(url);
  await a.locator('#createForm [name=player]').fill('Ana');
  await a.locator('#createForm [name=goal]').fill('Prueba automatizada de combate, sin IA');
  await a.locator('#createForm button').click();
  await a.locator('#app').waitFor({state:'visible'});
  const invite=await a.evaluate(async()=>{
   const token=localStorage.getItem('cronicas-token');
   return (await (await fetch('/api/state',{headers:{Authorization:'Bearer '+token}})).json()).invite;
  });
  await b.goto(url);await b.locator('#joinForm [name=name]').fill('Luis');
  await b.locator('#inviteInput').fill(invite);await b.locator('#joinForm button').click();
  await b.locator('#app').waitFor({state:'visible'});
  await a.reload();await a.locator('#app').waitFor({state:'visible'});
  async function character(name,enemy){
   await a.locator('#addCharacter').click();
   await a.locator('#modal details summary').last().click();await a.locator('#creatorManual').click();
   const form=a.locator('#characterForm');
   await form.locator('[name=name]').fill(name);
   await form.locator('[name=hp]').fill('20');await form.locator('[name=maxHp]').fill('20');
   await form.locator('[name=ac]').fill('14');await form.locator('[name=attack]').fill('4');
   await form.locator('[name=initiative]').fill(enemy?'-100':'100');
   await form.locator('[name=damage]').fill('1d6+2');
   await form.locator('[name=basicMelee]').check();await form.locator('[name=flatAc]').fill('12');
   if(enemy)await form.locator('[name=enemy]').check();
   else await form.locator('[name=owner]').selectOption({label:'Luis'});
   await form.locator('button.primary').click();await a.locator('#modal').waitFor({state:'hidden'});
  }
  await character('Aria',false);await character('Bandido',true);
  assert.equal(await a.locator('#board').isVisible(),true);await a.locator('#startCombat').click();
  await a.waitForFunction(()=>document.querySelector('#turnInfo').textContent.includes('Aria'));
  await b.reload();await b.locator('#app').waitFor({state:'visible'});
  assert.equal(await b.locator('#board').isVisible(),true);
  assert.equal(await b.locator('#attackButton').isEnabled(),true);
  await b.locator('#attackButton').click();
  await b.waitForFunction(()=>document.querySelector('#attackButton').disabled);
  await b.locator('[data-tab=story]').click();
  await b.getByText('Aria ataca a Bandido:',{exact:false}).waitFor();
  const state=await b.evaluate(async()=>{
   const token=localStorage.getItem('cronicas-token');
   return (await (await fetch('/api/state',{headers:{Authorization:'Bearer '+token}})).json()).state;
  });
  assert.equal(state.characters.find(c=>c.name==='Bandido').hp,12);
  assert.equal(state.messages.at(-1).combat.damage,8);
  assert.equal(await b.locator('#story').isVisible(),true);
  assert.equal(await b.locator('#board').isVisible(),true);
  // Finishing a player turn resolves the enemy and returns control in one save.
  await b.locator('#nextTurn').click();
  await b.waitForFunction(()=>document.querySelector('#attackButton').disabled===false);
  const afterEnemy=await b.evaluate(async()=>{
   const token=localStorage.getItem('cronicas-token');
   return (await (await fetch('/api/state',{headers:{Authorization:'Bearer '+token}})).json());
  });
  assert.equal(afterEnemy.state.characters.find(c=>c.name==='Aria').hp,12);
  assert.equal(afterEnemy.state.board.round,2);
  // A ruler and token selection only change local UI, never the shared version.
  await b.locator('#tool').selectOption('measure');
  await b.locator('[data-x="0"][data-y="0"]').click();
  await b.locator('[data-x="3"][data-y="2"]').click();
  assert.match(await b.locator('#pathInfo').textContent(),/20 pies/);
  assert.equal(await b.locator('#confirmMove').isDisabled(),true);
  await b.locator('#tool').selectOption('move');
  await b.locator('[data-x="0"][data-y="0"]').click();
  const localVersion=await b.evaluate(async()=>{
   const token=localStorage.getItem('cronicas-token');
   return (await (await fetch('/api/state',{headers:{Authorization:'Bearer '+token}})).json()).version;
  });
  assert.equal(localVersion,afterEnemy.version);
  // Explicit quick dice are saved, without enabling the AI checkbox's behavior.
  await b.locator('[data-quick-die="20"]').click();
  await b.getByText('Tirada rápida d20:',{exact:false}).waitFor();
  await a.reload();await a.locator('#app').waitFor({state:'visible'});
  await a.locator('[data-tab=story]').click();await a.getByText('Aria ataca a Bandido:',{exact:false}).waitFor();
  assert.deepEqual(errors,[]);
  assert.equal(await b.locator('#board').isVisible(),true);
  await b.screenshot({path:'.deps/combat-browser.png',fullPage:true});
  await b.setViewportSize({width:390,height:844});
  await b.locator('[data-tab=board]').click();
  assert.equal(await b.locator('#board').isVisible(),true);
  await b.locator('[data-tab=story]').click();
  assert.equal(await b.locator('#story').isVisible(),true);
  await b.screenshot({path:'.deps/tabletop-mobile.png',fullPage:true});
  assert.equal(await b.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
  assert.deepEqual(errors,[]);
  console.log('OK: two players, automatic enemies, ruler without writes, quick dice, desktop map/chat, mobile panels, no JS errors.');
 }finally{
  if(browser)await browser.close();
  fixture.kill();
 }
})().catch(error=>{console.error(error);process.exitCode=1});
