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
  await a.locator('[data-tab=board]').click();await a.locator('#startCombat').click();
  await a.waitForFunction(()=>document.querySelector('#turnInfo').textContent.includes('Aria'));
  await b.reload();await b.locator('#app').waitFor({state:'visible'});
  await b.locator('[data-tab=board]').click();
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
  await a.reload();await a.locator('#app').waitFor({state:'visible'});
  await a.locator('[data-tab=story]').click();await a.getByText('Aria ataca a Bandido:',{exact:false}).waitFor();
  assert.deepEqual(errors,[]);
  await b.locator('[data-tab=board]').click();
  await b.screenshot({path:'.deps/combat-browser.png',fullPage:true});
  console.log('OK: two browsers, profile setup, guest attack, automatic damage, action budget, shared persistence, no JS errors.');
 }finally{
  if(browser)await browser.close();
  fixture.kill();
 }
})().catch(error=>{console.error(error);process.exitCode=1});
