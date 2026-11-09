const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_ADVENTURE_FIXTURE:'1',TEST_CAMPAIGN_WORLD_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  let context=await browser.newContext({hasTouch:true,acceptDownloads:true}),page=await context.newPage();const actions=[],errors=[];
  const track=page=>{page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept())};track(page);
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Recordar a las personas del viaje');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  await page.locator('#beginAdventure').click();await page.locator('#adventureForm [name=source]').selectOption('generated');await page.locator('#adventureForm button').click();
  await page.waitForFunction(()=>snapshot?.state.campaignWorldView?.revision===1&&!busy);
  const id=await page.evaluate(()=>snapshot.id),characters=await page.evaluate(()=>structuredClone(snapshot.state.characters)),invite=await page.evaluate(()=>snapshot.invite);
  await page.locator('[data-tab=journal]').click();assert.equal(await page.locator('#campaignWorldJournal').evaluate(e=>e.open),false);
  const count=actions.length;await page.locator('#campaignWorldJournal > summary').focus();await page.keyboard.press('Enter');
  assert.equal(actions.length,count);assert.match(await page.locator('#campaignWorldNotes').textContent(),/Arda/);assert.match(await page.locator('#campaignWorldNotes').textContent(),/Archivo/);
  assert.doesNotMatch(await page.locator('#campaignWorldNotes').textContent(),/PRIVATE|SECRET/);
  const guest=await browser.newContext({hasTouch:true}),guestPage=await guest.newPage();track(guestPage);
  await guestPage.goto(url+'/?invite='+encodeURIComponent(invite));await guestPage.locator('#joinForm [name=name]').fill('Luis');await guestPage.locator('#joinForm button').click();await guestPage.waitForFunction(()=>snapshot?.state.campaignWorldView&&!busy);
  assert.doesNotMatch(JSON.stringify(await guestPage.evaluate(()=>snapshot)),/PRIVATE|SECRET/);
  await guestPage.locator('[data-tab=journal]').click();await guestPage.locator('#campaignWorldJournal > summary').tap();assert.match(await guestPage.locator('#campaignWorldNotes').textContent(),/Arda/);
  await page.reload();await page.waitForFunction(()=>snapshot?.state.campaignWorldView&&!busy);
  await page.locator('#speaker').selectOption(characters[0].id);await page.locator('#messageKind').selectOption('dialogue');await page.locator('#message').fill('Saludo a Arda y recuerdo nuestra conversación.');await page.locator('#send').click();
  await page.waitForFunction(()=>snapshot.state.campaignWorldView.revision===2&&!busy);
  assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),characters);
  await page.locator('[data-tab=journal]').click();await page.locator('#campaignWorldJournal > summary').click();assert.match(await page.locator('#campaignWorldNotes').textContent(),/recuerda vuestra conversación/);assert.match(await page.locator('#campaignWorldNotes').textContent(),/Vínculos/);
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
  await page.locator('#exitBtn').click();const storage=await context.storageState();await context.close();context=await browser.newContext({storageState:storage,hasTouch:true});page=await context.newPage();track(page);await page.goto(url);
  await page.locator('#savedCampaigns [data-library-open]:not([data-library-character])').focus();await page.keyboard.press('Enter');await page.waitForFunction(()=>snapshot?.state.campaignWorldView?.revision===2&&!busy);assert.equal(await page.evaluate(()=>snapshot.id),id);
  await page.setViewportSize({width:390,height:1000});await page.locator('[data-tab=journal]').tap();await page.locator('#campaignWorldJournal > summary').tap();assert.match(await page.locator('#campaignWorldNotes').textContent(),/Vínculos/);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/campaign-world-mobile.png',fullPage:true});assert.deepEqual(errors,[]);
  assert.equal(actions.filter(a=>a.type==='start_adventure').length,1);assert.equal(actions.filter(a=>a.type==='talk'&&a.director).length,1);
  console.log('World notes: guided creator, explicit new start, known people/places/links, hidden secrets, keyboard/touch/mobile, unchanged sheets, copy, close/rejoin same campaign; 2 simulated replies, zero real inference.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
