const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process');
const {createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const host=await browser.newContext(),guest=await browser.newContext();
  const token=(await (await host.request.post(url+'/api/create',{data:{player:'Ana',title:'Checks'}})).json()).token;
  const headers={Authorization:'Bearer '+token};
  const room=await (await host.request.get(url+'/api/state',{headers})).json();
  const player=(await (await guest.request.post(url+'/api/join',{data:{name:'Luis',invite:room.invite}})).json()).token;
  const gh={Authorization:'Bearer '+player};let roomVersion=(await (await guest.request.get(url+'/api/state',{headers:gh})).json()).version;
  const added=await guest.request.post(url+'/api/action',{headers:gh,data:{id:'new-character',version:roomVersion,type:'character',character:{name:'Aria',abilities:[9,16,12,10,14,8],saves:[4,6,2],skillTotals:[{name:'Percepción',total:8}]}}});assert.ok(added.ok());
  await host.addInitScript(t=>localStorage.setItem('cronicas-token',t),token);await guest.addInitScript(t=>localStorage.setItem('cronicas-token',t),player);
  const a=await host.newPage(),b=await guest.newPage(),errors=[];
  for(const page of [a,b]){page.on('pageerror',e=>errors.push(e.message));await page.goto(url);await page.locator('#app').waitFor({state:'visible'})}
  assert.equal(await b.locator('#requestCheck').isVisible(),false);
  await b.locator('.party-person').click();
  assert.equal(await b.locator('[data-check-key="str"]').textContent(),'Fuerza -1');
  await b.locator('[data-check-key="Percepción"]').click();
  await b.waitForFunction(()=>snapshot.state.messages.at(-1).check?.total===20);
  await b.locator('#closeModal').click();
  await a.reload();await a.locator('#app').waitFor({state:'visible'});
  await a.locator('#requestCheck').click();
  await a.locator('#requestCheckForm [name=selection]').selectOption('6');
  await a.locator('#requestCheckForm [name=dc]').fill('16');
  await a.locator('#requestCheckForm [name=reason]').fill('Resistir el peligro');
  await a.locator('#requestCheckForm button').click();await a.locator('.check-request').waitFor();
  await b.reload();await b.locator('.check-request').waitFor();
  await b.locator('[data-resolve-check]').click();await b.locator('.check-request').waitFor({state:'detached'});
  await b.waitForFunction(()=>snapshot.state.messages.at(-1).check?.success===true);
  assert.match(await b.locator('#messages').textContent(),/contra CD 16: éxito/);
  await a.reload();await a.locator('#app').waitFor({state:'visible'});assert.equal(await a.locator('.check-request').count(),0);
  // Saving a legacy-style sheet retains the new prepared skill totals.
  await b.locator('.party-person').click();
  assert.equal(await b.locator('[name=skillTotalsInput]').inputValue(),'Percepción | 8');
  await b.locator('#characterForm [name=skillTotalsInput]').fill('Percepción | 8\nSigilo | 5');
  await b.locator('#characterForm button.primary').click();await b.locator('#modal').waitFor({state:'hidden'});
  await b.locator('.party-person').click();assert.equal(await b.locator('[data-check-key="Sigilo"]').textContent(),'Sigilo +5');
  await b.setViewportSize({width:390,height:844});
  await b.locator('.sheet-checks').scrollIntoViewIfNeeded();
  assert.equal(await b.locator('#modal').evaluate(el=>el.scrollWidth<=el.clientWidth),true);
  await b.screenshot({path:'.deps/checks-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);console.log('OK: sheet checks, stored modifiers, host request, player roll, automatic DC result, two-client persistence, skill editing and mobile. No AI.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
