const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_ADVENTURE_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{createInterface({input:fixture.stdout}).once('line',resolve);fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const page=await browser.newPage({hasTouch:true}),actions=[],errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Explorar');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  let interrupt=true;
  await page.route('**/api/action',async route=>{if(interrupt&&route.request().postDataJSON().type==='talk'){interrupt=false;await route.fetch();await route.abort('connectionfailed')}else await route.continue()});
  await page.setViewportSize({width:390,height:1000});await page.locator('#messageKind').selectOption('action');await page.locator('#message').fill('Observo el patio.');await page.locator('#useAI').check();await page.locator('#send').tap();
  await page.waitForFunction(()=>!busy&&localStorage.getItem('cronicas-pending')!==null);
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('cronicas-pending')).body);
  assert.equal(saved.captureContract,'pf-director-action-1');assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.speaker==='Director · Claude Haiku').length),1);
  await page.reload();await page.waitForFunction(()=>!!snapshot&&!busy&&localStorage.getItem('cronicas-pending')===null);
  const submissions=actions.filter(a=>a.type==='talk');assert.equal(submissions.length,2);assert.deepEqual(submissions[0],submissions[1]);
  assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.speaker==='Director · Claude Haiku').length),1);
  assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.text==='Observo el patio.').length),1);
  // A pending body saved by an older client must retain its original contract.
  const old=await page.evaluate(async()=>{const body={id:crypto.randomUUID(),version:snapshot.version,type:'talk',kind:'action',text:'Observo de nuevo.',director:true};localStorage.setItem('cronicas-pending',JSON.stringify({token,body}));await api('/api/action',body);return body});
  await page.reload();await page.waitForFunction(()=>!!snapshot&&!busy&&localStorage.getItem('cronicas-pending')===null);
  const oldSubmissions=actions.filter(a=>a.id===old.id);assert.equal(oldSubmissions.length,2);assert.deepEqual(oldSubmissions,[old,old]);assert.ok(!('captureContract' in oldSubmissions[1]));
  assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.text==='Observo de nuevo.').length),1);assert.deepEqual(errors,[]);
  console.log('Director action capture browser verified: mobile declaration carries new contract; lost committed response retains exact submission; reload retries same id/body and restores one player message and one director response. Provider simulated.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
