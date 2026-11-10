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
  let interrupted=0,failSent,releaseFail;const lateDialog=process.env.TEST_PENDING_LATE_DIALOG==='1',failureRequested=new Promise(resolve=>{failSent=resolve}),failureGate=new Promise(resolve=>{releaseFail=resolve});
  await page.route('**/api/action',async route=>{if(route.request().postDataJSON().type==='talk'&&interrupted<2){interrupted++;if(interrupted===1)await route.fetch();if(interrupted===2&&lateDialog){failSent();await failureGate}if(interrupted===1&&process.env.TEST_UNREADABLE_REPLY==='1')await route.fulfill({status:502,contentType:'text/html',body:'Temporary proxy failure'});else await route.abort('connectionfailed')}else await route.continue()});
  await page.setViewportSize(process.env.TEST_PENDING_SHORT_VIEWPORT==='1'?{width:844,height:390}:{width:390,height:1000});await page.locator('#messageKind').selectOption('action');await page.locator('#message').fill('Observo el patio.');await page.locator('#useAI').check();await page.locator('#send').tap();
  await page.waitForFunction(()=>!busy&&localStorage.getItem('cronicas-pending')!==null);
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('cronicas-pending')).body);
  assert.match(await page.locator('#toast').textContent(),process.env.TEST_UNREADABLE_REPLY==='1'?/respuesta válida/:/No se pudo conectar con la mesa/);
  const keepDraft=process.env.TEST_KEEP_DRAFT==='1';if(keepDraft)await page.locator('#message').fill('Borrador para después.');
  assert.equal(saved.captureContract,'pf-director-action-1');assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.speaker==='Director · Claude Haiku').length),1);
  assert.equal(await page.locator('#playGuidanceAction').textContent(),'Recuperar envío');
  if(process.env.TEST_PENDING_SHORT_VIEWPORT==='1'){const button=await page.locator('#playGuidanceAction').boundingBox();assert.ok(button.y>=0&&button.y+button.height<=390,'Recovery remains visible in a short viewport');assert.ok(await page.locator('#story').evaluate(element=>element.clientHeight>=200))}
  if(process.env.TEST_PENDING_PASSIVE_DIALOG==='1'){await page.locator('#libraryBtn').click();const focus=await page.evaluateHandle(()=>document.activeElement),before=actions.length;await page.evaluate(()=>window.dispatchEvent(new StorageEvent('storage',{key:'cronicas-pending',newValue:localStorage.getItem('cronicas-pending')})));assert.equal(await page.locator('#modal').evaluate(element=>element.open),true,'A passive receipt update must preserve the current dialog');assert.equal(await focus.evaluate(element=>element===document.activeElement),true);assert.equal(actions.length,before);await focus.dispose();await page.locator('#closeModal').click()}
  await page.locator('#playGuidance').scrollIntoViewIfNeeded();await page.screenshot({path:'.deps/pending-guidance-mobile.png',fullPage:true});
  const count=actions.length;await page.locator('[data-tab=journal]').click();await page.locator('[data-tab=story]').click();assert.equal(actions.length,count);
  await page.locator('#playGuidanceAction').focus();await page.keyboard.press('Enter');
  if(lateDialog){await failureRequested;await page.locator('#libraryBtn').click();const focus=await page.evaluateHandle(()=>document.activeElement);releaseFail();await page.waitForFunction(()=>!busy);assert.equal(await page.locator('#modal').evaluate(element=>element.open),true,'A late failed recovery must preserve a newer dialog');assert.match(await page.locator('#modalContent h2').textContent(),/Partidas y personajes/);assert.equal(await focus.evaluate(element=>element===document.activeElement),true,'Recovery must preserve focus in the newer dialog');await focus.dispose();await page.locator('#closeModal').click()}
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
