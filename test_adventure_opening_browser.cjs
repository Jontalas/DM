const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_ADVENTURE_FIXTURE:'0',TEST_CAMPAIGN_WORLD_FIXTURE:'0'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  for(const source of ['example','route']){
   const context=await browser.newContext({hasTouch:true,acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[];
   page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Jugar una aventura preparada');await page.locator('#createForm button').click();
   await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
   assert.equal(await page.evaluate(()=>model.aiConfigured),false);assert.equal(await page.locator('#beginAdventure').isEnabled(),true);
   const count=actions.length;await page.locator('#beginAdventure').focus();await page.keyboard.press('Enter');
   assert.equal(await page.locator('#adventureForm [name=source]').inputValue(),'example');assert.equal(actions.length,count);
   await page.locator('#adventureForm [name=source]').selectOption('generated');assert.equal(await page.locator('#adventureForm button').isDisabled(),true);assert.match(await page.locator('#adventureSourceHint').textContent(),/director no está disponible/);
   await page.locator('#adventureForm [name=source]').selectOption(source);assert.match(await page.locator('#adventureSourceHint').textContent(),/no llama a IA/);
   const original=await page.evaluate(()=>structuredClone(snapshot.state.characters));await page.locator('#adventureForm button').click();await page.waitForFunction(()=>snapshot?.state.preparedOpening&&!busy);
   assert.equal(actions.at(-1).openingContract,'authored-opening-1');assert.equal(actions.at(-1).captureContract,'pf-authored-opening-1');assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.kind==='director').length),0);assert.equal(await page.locator('.message.scene').count(),1);
   assert.equal(await page.locator('#useAI').isDisabled(),true);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),original);assert.equal(await page.evaluate(()=>snapshot.state.moduleProgress.discoveries.length),0);
   if(source==='example'){
    for(let search=0;search<2;search++){const version=await page.evaluate(()=>snapshot.version);await page.locator('#investigationForm button[value=take20]').click();await page.waitForFunction(v=>snapshot.version>v&&!busy,version)}
    assert.equal(await page.evaluate(()=>snapshot.state.moduleProgress.completed),true);assert.equal(await page.locator('#nextAdventure').isDisabled(),true);assert.match(await page.locator('#nextAdventureHint').textContent(),/director no está disponible/);
   }else{assert.equal(await page.locator('[data-route-exit]').count(),2);await page.locator('[data-route-exit=estantes]').click();await page.waitForFunction(()=>snapshot.state.adventureRouteView.current==='estantes'&&!busy)}
   await page.setViewportSize({width:390,height:1000});await page.locator('[data-tab=journal]').tap();const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
   await page.reload();await page.waitForFunction(()=>snapshot?.state.preparedOpening&&!busy);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),original);assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.kind==='director').length),0);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/authored-opening-'+source+'-mobile.png',fullPage:true});assert.deepEqual(errors,[]);await context.close();
  }
  console.log('Authored starts without configured AI: guided creator, automatic prepared choice, unavailable generation explained, exact scene/hidden clues, investigation or route, original receipt, copy/reload/keyboard/touch/mobile, zero director replies and no fake provider.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
