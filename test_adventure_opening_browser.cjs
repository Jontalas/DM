const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_ADVENTURE_FIXTURE:'0',TEST_CAMPAIGN_WORLD_FIXTURE:'0'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  for(const source of ['example','route']){
   const context=await browser.newContext({hasTouch:true,acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[],apiRequests=[];
   page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().includes('/api/'))apiRequests.push(r.url());if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');
   assert.equal(await page.locator('#campaignOptions').evaluate(e=>e.open),false);
   const entryRequests=apiRequests.length;await page.locator('#campaignOptions > summary').focus();await page.keyboard.press('Enter');await page.keyboard.press('Enter');assert.equal(apiRequests.length,entryRequests);
   if(source==='route')await page.locator('#createForm [name=goal]').fill('Jugar una aventura preparada');
   await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/entry-simplified-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:960});
   await page.locator('#createForm button').click();await page.waitForFunction(()=>snapshot&&!busy);assert.ok(await page.evaluate(()=>snapshot.state.goal.trim()));
   assert.equal(await page.locator('#adventureEntry').isVisible(),false);assert.equal(await page.locator('[data-create-hero]').count(),1);assert.equal(await page.locator('#messages .empty').count(),0);
   if(source==='example'){await page.setViewportSize({width:390,height:844});await page.locator('[data-create-hero]').scrollIntoViewIfNeeded();await page.screenshot({path:'.deps/first-character-step-mobile.png'});await page.setViewportSize({width:1440,height:960})}
   await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');const beforeReview=actions.length;await page.locator(source==='example'?'#creatorName':'#creatorReview').focus();await page.keyboard.press('Enter');assert.equal(actions.length,beforeReview);assert.equal(await page.locator('[data-creator-step="3"]').getAttribute('aria-current'),'step');
   assert.equal(await page.locator('.creator-calculation').evaluate(e=>e.open),false);const reviewRequests=apiRequests.length;await page.locator('.creator-calculation > summary').focus();await page.keyboard.press('Enter');await page.keyboard.press('Enter');assert.equal(apiRequests.length,reviewRequests);
   if(source==='example'){await page.setViewportSize({width:390,height:900});await page.locator('#creatorFinish').scrollIntoViewIfNeeded();await page.screenshot({path:'.deps/creator-quick-review-mobile.png'});await page.setViewportSize({width:1440,height:960})}
   await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();const followRequests=apiRequests.length;
   if(source==='example'){assert.equal(await page.locator('#creatorContinue').textContent(),'Elegir aventura');await page.locator('#creatorContinue').focus();await page.keyboard.press('Enter');assert.equal(apiRequests.length,followRequests)}else await page.locator('#closeModal').click();
   assert.equal(await page.evaluate(()=>model.aiConfigured),false);assert.equal(await page.locator('#beginAdventure').isEnabled(),true);
   if(source==='route'){await page.setViewportSize({width:390,height:900});assert.equal(await page.locator('#story>.chapter').isVisible(),false);await page.locator('#beginAdventure').scrollIntoViewIfNeeded();await page.screenshot({path:'.deps/ready-to-choose-adventure-mobile.png'});await page.setViewportSize({width:1440,height:960})}
   const count=actions.length;if(source!=='example'){await page.locator('#beginAdventure').focus();await page.keyboard.press('Enter')}
   assert.equal(await page.locator('#adventureForm [name=source]').inputValue(),'example');assert.equal(actions.length,count);
   const asyncPreparation=process.env.TEST_OPENING_ASYNC==='1'&&source==='example';
   if(asyncPreparation){
    await page.locator('#adventureForm [name=source]').selectOption('text');
    await page.evaluate(()=>{window.originalArrayBuffer=File.prototype.arrayBuffer;File.prototype.arrayBuffer=function(){if(this.name!=='delayed-source.txt')return window.originalArrayBuffer.call(this);return new Promise(resolve=>{window.releaseSourceRead=()=>window.originalArrayBuffer.call(this).then(resolve)})};const input=document.querySelector('#adventureForm [name=sourceFile]'),handler=input.onchange;input.onchange=e=>{window.sourceReadFinished=handler(e);return window.sourceReadFinished}});
    await page.locator('#adventureForm [name=sourceFile]').setInputFiles({name:'delayed-source.txt',mimeType:'text/plain',buffer:Buffer.from('Texto anterior del archivo, sin decisiones del personaje.')});await page.waitForFunction(()=>!!window.releaseSourceRead);
    await page.locator('#closeModal').click();await page.locator('#beginAdventure').click();await page.locator('#adventureForm [name=source]').selectOption('text');await page.locator('#adventureForm [name=sourceText]').fill('Este borrador nuevo debe conservarse.');
    await page.evaluate(()=>window.releaseSourceRead());await page.evaluate(()=>window.sourceReadFinished);assert.equal(await page.locator('#adventureForm [name=sourceText]').inputValue(),'Este borrador nuevo debe conservarse.');assert.equal(actions.length,count);
    await page.evaluate(()=>{const input=document.querySelector('#adventureForm [name=sourceFile]'),handler=input.onchange;input.onchange=e=>{window.sourceReadFinished=handler(e);return window.sourceReadFinished}});
    await page.locator('#adventureForm [name=sourceFile]').setInputFiles({name:'delayed-source.txt',mimeType:'text/plain',buffer:Buffer.from('Otro texto que no debe sustituir la edición.')});await page.locator('#adventureForm [name=sourceText]').fill('Edición mientras se lee el archivo.');await page.evaluate(()=>window.releaseSourceRead());await page.evaluate(()=>window.sourceReadFinished);assert.equal(await page.locator('#adventureForm [name=sourceText]').inputValue(),'Edición mientras se lee el archivo.');assert.equal(actions.length,count);
    await page.evaluate(()=>{File.prototype.arrayBuffer=window.originalArrayBuffer});
    await page.locator('#adventureForm [name=source]').selectOption('import');
    await page.evaluate(()=>{window.originalFileText=File.prototype.text;File.prototype.text=function(){if(this.name!=='delayed-adventure.json')return window.originalFileText.call(this);return new Promise(resolve=>{window.releaseModuleRead=()=>window.originalFileText.call(this).then(resolve)})};const form=document.querySelector('#adventureForm'),handler=form.onsubmit;form.onsubmit=e=>{window.preparationFinished=handler(e);return window.preparationFinished}});
    await page.locator('#adventureForm [name=moduleFile]').setInputFiles({name:'delayed-adventure.json',mimeType:'application/json',buffer:fs.readFileSync('adventures/la-carta-perdida.json')});const beforePreparation=await page.evaluate(()=>structuredClone(snapshot));await page.locator('#adventureForm button').click();await page.waitForFunction(()=>!!window.releaseModuleRead);
    await page.locator('#closeModal').click();await page.locator('#libraryBtn').click();await page.evaluate(()=>window.releaseModuleRead());await page.evaluate(()=>window.preparationFinished);assert.equal(actions.length,count,'Closing before the file is read must not start an adventure');assert.equal(await page.locator('#modal').evaluate(e=>e.open),true);assert.match(await page.locator('#modalContent h2').textContent(),/Partidas y personajes/);assert.deepEqual(await page.evaluate(()=>snapshot.state),beforePreparation.state);
    await page.evaluate(()=>{File.prototype.text=window.originalFileText});await page.locator('#closeModal').click();await page.locator('#beginAdventure').click();
   }
   assert.match(await page.locator('#adventureChoiceDescription').textContent(),/Lucio/);assert.doesNotMatch(await page.locator('#adventureChoiceDescription').textContent(),/forro/);
   const choiceRequests=apiRequests.length;await page.locator('#adventureForm [name=source]').selectOption('route');assert.match(await page.locator('#adventureChoiceDescription').textContent(),/Ruta individual/);assert.equal(apiRequests.length,choiceRequests);
   await page.locator('#adventureForm [name=source]').selectOption('generated');assert.equal(await page.locator('#adventureForm button').isDisabled(),true);assert.match(await page.locator('#adventureSourceHint').textContent(),/director no está disponible/);
   await page.locator('#adventureForm [name=source]').selectOption(source);assert.match(await page.locator('#adventureSourceHint').textContent(),/no llama a IA/);
   await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/adventure-choice-'+source+'-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:960});
   let openingRequested,releaseOpening;const requestedOpening=new Promise(resolve=>{openingRequested=resolve}),openingGate=new Promise(resolve=>{releaseOpening=resolve});
   if(asyncPreparation){await page.route('**/api/action',async route=>{const response=await route.fetch();assert.equal(response.ok(),true);openingRequested();await openingGate;await route.fulfill({response})},{times:1});await page.evaluate(()=>{const form=document.querySelector('#adventureForm'),handler=form.onsubmit;form.onsubmit=e=>{window.preparationFinished=handler(e);return window.preparationFinished}})}
   const original=await page.evaluate(()=>structuredClone(snapshot.state.characters));await page.locator('#adventureForm button').click();
   if(asyncPreparation){await requestedOpening;await page.locator('#closeModal').click();await page.locator('#libraryBtn').click();releaseOpening();await page.evaluate(()=>window.preparationFinished);assert.equal(await page.locator('#modal').evaluate(e=>e.open),true,'A late opening reply must preserve the newer dialog');assert.match(await page.locator('#modalContent h2').textContent(),/Partidas y personajes/);await page.locator('#closeModal').click();await page.locator('[data-tab=story]').click()}
   await page.waitForFunction(()=>snapshot?.state.preparedOpening&&!busy);
   assert.equal(actions.at(-1).openingContract,'authored-opening-1');assert.equal(actions.at(-1).captureContract,'pf-authored-opening-1');assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.kind==='director').length),0);assert.equal(await page.locator('.message.scene').count(),1);
   assert.equal(await page.locator('#useAI').isDisabled(),true);assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),original);assert.equal(await page.evaluate(()=>snapshot.state.moduleProgress.discoveries.length),0);
   if(source==='example'){
    await page.setViewportSize({width:1440,height:960});
    assert.equal(await page.locator('.character-preparation details').evaluate(e=>e.open),false);
    assert.equal(await page.locator('.scene-recap').evaluate(e=>e.open),false);
    assert.equal(await page.locator('#investigationMethods').evaluate(e=>e.open),false);
    assert.equal(await page.evaluate(()=>!!(document.querySelector('#messages').compareDocumentPosition(document.querySelector('#investigationPanel'))&Node.DOCUMENT_POSITION_FOLLOWING)),true);
    const io=apiRequests.length;await page.locator('.character-preparation summary').focus();await page.keyboard.press('Enter');assert.equal(await page.locator('.character-preparation .rule-link').count(),7);await page.keyboard.press('Enter');
    await page.locator('.scene-recap summary').focus();await page.keyboard.press('Enter');await page.keyboard.press('Enter');assert.equal(apiRequests.length,io);
    await page.locator('#investigationMethods summary').focus();await page.keyboard.press('Enter');assert.match(await page.locator('#investigationMethods').textContent(),/no garantiza/);await page.keyboard.press('Enter');assert.equal(apiRequests.length,io);
    assert.equal(await page.locator('#board').isVisible(),true);assert.equal(await page.locator('#story').isVisible(),true);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.waitForFunction(()=>document.querySelector('#toast').hidden);await page.screenshot({path:'.deps/table-presentation-desktop.png'});
    await page.setViewportSize({width:390,height:1000});await page.locator('[data-tab=story]').tap();assert.equal(await page.locator('#sceneTitle').isVisible(),true);await page.locator('.message.scene').scrollIntoViewIfNeeded();await page.screenshot({path:'.deps/table-presentation-mobile-story.png'});
    await page.locator('[data-tab=board]').tap();assert.equal(await page.locator('#board').isVisible(),true);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/table-presentation-mobile-board.png'});
    await page.locator('[data-tab=story]').tap();await page.setViewportSize({width:1440,height:960});
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
