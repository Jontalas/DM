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
  let interrupted=0;
  await page.route('**/api/action',async route=>{if(route.request().postDataJSON().type==='talk'&&interrupted<2){interrupted++;if(interrupted===1)await route.fetch();await route.abort('connectionfailed')}else await route.continue()});
  await page.setViewportSize({width:390,height:1000});await page.locator('#messageKind').selectOption('action');await page.locator('#message').fill('Observo el patio.');await page.locator('#useAI').check();await page.locator('#send').tap();
  await page.waitForFunction(()=>!busy&&localStorage.getItem('cronicas-pending')!==null);
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('cronicas-pending')).body);
  const keepDraft=process.env.TEST_KEEP_DRAFT==='1';if(keepDraft)await page.locator('#message').fill('Borrador para después.');
  assert.equal(saved.captureContract,'pf-director-action-1');assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.speaker==='Director · Claude Haiku').length),1);
  assert.equal(await page.locator('#playGuidanceAction').textContent(),'Recuperar envío');
  await page.locator('#playGuidance').scrollIntoViewIfNeeded();await page.screenshot({path:'.deps/pending-guidance-mobile.png',fullPage:true});
  const count=actions.length;await page.locator('[data-tab=journal]').click();await page.locator('[data-tab=story]').click();assert.equal(actions.length,count);
  await page.locator('#playGuidanceAction').focus();await page.keyboard.press('Enter');
  await page.waitForFunction(()=>!busy&&localStorage.getItem('cronicas-pending')!==null);
  assert.deepEqual(await page.evaluate(()=>JSON.parse(localStorage.getItem('cronicas-pending')).body),saved);
  assert.equal(await page.locator('#playGuidanceAction').isEnabled(),true);
  await page.locator('#playGuidanceAction').tap();await page.waitForFunction(()=>!busy&&localStorage.getItem('cronicas-pending')===null);
  const submissions=actions.filter(a=>a.type==='talk');assert.equal(submissions.length,3);for(const body of submissions)assert.deepEqual(body,saved);
  assert.notEqual(await page.locator('#playGuidanceAction').textContent(),'Recuperar envío');
  assert.equal(await page.locator('#message').inputValue(),keepDraft?'Borrador para después.':'');
  assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.speaker==='Director · Claude Haiku').length),1);
  assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.text==='Observo el patio.').length),1);
  await page.evaluate(()=>{localStorage.setItem('cronicas-pending',JSON.stringify({token:'another-campaign',body:{type:'talk'}}));renderPlayGuidance(snapshot.state)});
  assert.notEqual(await page.locator('#playGuidanceAction').textContent(),'Recuperar envío');await page.evaluate(()=>localStorage.removeItem('cronicas-pending'));
  assert.deepEqual(errors,[]);
  console.log('Pending guidance verified: mobile persistent recovery, local navigation without POST, keyboard retry still offline retains exact body, touch retry restores one response without reload; no fresh declaration. Provider simulated.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
