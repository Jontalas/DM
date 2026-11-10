const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process');const {createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const host=await browser.newContext(),guest=await browser.newContext({hasTouch:true});
  const token=(await (await host.request.post(url+'/api/create',{data:{player:'Ana',title:'Creation'}})).json()).token;
  const headers={Authorization:'Bearer '+token};const room=await (await host.request.get(url+'/api/state',{headers})).json();
  const player=(await (await guest.request.post(url+'/api/join',{data:{name:'Luis',invite:room.invite}})).json()).token;
  await host.addInitScript(t=>localStorage.setItem('cronicas-token',t),token);await guest.addInitScript(t=>localStorage.setItem('cronicas-token',t),player);
  const a=await host.newPage(),b=await guest.newPage(),errors=[],actions=[];
  for(const page of [a,b])page.on('pageerror',e=>errors.push(e.message));
  b.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await b.goto(url);await b.locator('#app').waitFor({state:'visible'});
  const asyncCatalog=process.env.TEST_CREATOR_CATALOG_ASYNC==='1';let catalogSent,releaseCatalog,catalogReads=0;const catalogRequested=new Promise(resolve=>{catalogSent=resolve}),catalogGate=new Promise(resolve=>{releaseCatalog=resolve});
  if(asyncCatalog){await b.route('**/creation-catalog.json*',async route=>{catalogReads++;const response=await route.fetch();catalogSent();await catalogGate;await route.fulfill({response})});await b.evaluate(()=>{const start=startCharacterCreator;startCharacterCreator=(...args)=>{window.creatorOpening=start(...args);return window.creatorOpening}})}
  const failedCatalog=process.env.TEST_CREATOR_CATALOG_FAILURE==='1';let failedCatalogReads=0;
  if(failedCatalog)await b.route('**/creation-catalog.json*',async route=>{failedCatalogReads++;if(failedCatalogReads===1)await route.fulfill({status:503,body:'Unavailable'});else await route.continue()});
  await b.locator('[data-create-hero]').click();
  if(failedCatalog){await b.locator('#creatorRetry').waitFor();assert.equal(actions.length,0);assert.match(await b.locator('#modalContent').textContent(),/partida sigue intacta/);await b.locator('#creatorRetry').focus();await b.keyboard.press('Enter');await b.locator('#creatorForm').waitFor();assert.equal(failedCatalogReads,2)}
  if(asyncCatalog){await catalogRequested;if(await b.locator('#modal').evaluate(element=>element.open))await b.locator('#closeModal').click();await b.locator('#libraryBtn').click();releaseCatalog();await b.evaluate(()=>window.creatorOpening);assert.match(await b.locator('#modalContent h2').textContent(),/Partidas y personajes/,'A late creator catalog must preserve the newer dialog');assert.equal(actions.length,0);await b.locator('#closeModal').click();await b.locator('[data-create-hero]').click();assert.equal(catalogReads,1)}
  await b.locator('#creatorForm').waitFor();
  assert.equal(await b.locator('#creatorName').evaluate(e=>e===document.activeElement),true);
  assert.equal(await b.locator('#creatorEnemy').count(),0);
  assert.equal(await b.locator('[data-creator-preset=guardian]').getAttribute('aria-pressed'),'true');
  await b.locator('[data-creator-preset=vanguard]').focus();await b.keyboard.press('Enter');assert.equal(await b.locator('[data-creator-preset=vanguard]').evaluate(e=>e===document.activeElement),true);await b.locator('#creatorName').fill('Aria');assert.equal(await b.locator('[data-creator-preset=vanguard]').getAttribute('aria-pressed'),'true');assert.equal(await b.locator('[data-creator-preset=guardian]').getAttribute('aria-pressed'),'false');assert.equal(actions.length,0);
  await b.setViewportSize({width:390,height:900});assert.ok(await b.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await b.screenshot({path:'.deps/creator-concept-mobile.png'});await b.setViewportSize({width:1280,height:900});
  await b.locator('#creatorNext').focus();await b.keyboard.press('Enter');assert.equal(await b.locator('#creatorPage').evaluate(e=>e===document.activeElement),true);await b.keyboard.press('Tab');assert.equal(await b.locator('[data-creator-ability="0"]').evaluate(e=>e===document.activeElement),true);await b.locator('[data-creator-ability="0"]').fill('18');
  assert.match(await b.locator('#creatorErrors').textContent(),/20 puntos/);
  await b.locator('[data-creator-ability="0"]').fill('16');await b.locator('#creatorNext').click();
  assert.equal(await b.locator('#creatorRanks').textContent(),'3 / 3 rangos asignados · 3 / 3 dotes · 0 / 0 idiomas adicionales');
  await b.locator('#creatorNext').click();assert.match(await b.locator('#creatorPreview').textContent(),/2d6\+6/);
  assert.equal(actions.length,0);const delayedCreator=process.env.TEST_CREATOR_LATE_DIALOG||'',mutableInput=process.env.TEST_CREATOR_MUTABLE_INPUT==='1',lostCreation=process.env.TEST_CREATOR_LOST_RESPONSE==='1';let createSent,releaseCreate;const createRequested=new Promise(resolve=>{createSent=resolve}),createGate=new Promise(resolve=>{releaseCreate=resolve});
  if(delayedCreator)await b.route('**/api/action',async route=>{const response=await route.fetch();assert.equal(response.status(),200);createSent();await createGate;if(lostCreation)await route.fulfill({status:503,json:{error:'Se perdió la respuesta al guardar'}});else await route.fulfill({response})},{times:1});
  if(delayedCreator||mutableInput)await b.evaluate(()=>{const form=document.querySelector('#creatorForm'),handler=form.onsubmit;form.onsubmit=event=>{window.creationFinished=handler(event);return window.creationFinished}});
  if(mutableInput){await b.evaluate(()=>{const original=act;act=(type,data)=>{if(type==='create_character')window.creationInput=data;return original(type,data)};window.creationReservation=navigator.locks.request('cronicas-pending',()=>new Promise(resolve=>{window.releaseCreationReservation=resolve}))});await b.waitForFunction(()=>!!window.releaseCreationReservation)}
  await b.locator('#creatorFinish').click();
  if(mutableInput){await b.waitForFunction(()=>busy);await b.evaluate(()=>{window.creationInput.choices.name='Nombre modificado después de confirmar';window.releaseCreationReservation()});await b.evaluate(()=>window.creationFinished);assert.equal(actions[0].choices.name,'Aria','Queued creation must use the choices confirmed before later mutation')}
  if(delayedCreator){await createRequested;assert.equal(await b.locator('#modalContent button:enabled, #modalContent input:enabled, #modalContent select:enabled').count(),0,'Confirmed choices stay locked while saving');assert.match(await b.locator('#creatorErrors').textContent(),/Guardando a Aria/);await b.locator('#closeModal').click();if(delayedCreator==='draft'){await b.locator('[data-create-hero]').click();await b.locator('#creatorName').fill('Lina')}else await b.locator('#libraryBtn').click();releaseCreate();await b.evaluate(()=>window.creationFinished);
   assert.equal(await b.locator('#modal').evaluate(element=>element.open),true,'A late result or failure must preserve the newer dialog');if(delayedCreator==='draft'){assert.equal(await b.locator('#creatorName').inputValue(),'Lina');assert.equal(await b.evaluate(()=>JSON.parse(sessionStorage.getItem('cronicas-creator:'+snapshot.id+':'+snapshot.me.id)).choices.name),'Lina')}else assert.match(await b.locator('#modalContent h2').textContent(),/Partidas y personajes/,'A late creation result must preserve the newer dialog');await b.locator('#closeModal').click();
   if(lostCreation){assert.equal(await b.locator('#playGuidanceAction').textContent(),'Recuperar envío');await b.locator('#playGuidanceAction').click();await b.waitForFunction(()=>!busy&&!localStorage.getItem('cronicas-pending'));assert.equal(actions.length,2);assert.deepEqual(actions[1],actions[0]);assert.equal(await b.evaluate(()=>snapshot.state.characters.length),1);if(delayedCreator==='draft')assert.equal(await b.evaluate(()=>JSON.parse(sessionStorage.getItem('cronicas-creator:'+snapshot.id+':'+snapshot.me.id)).choices.name),'Lina')}
   await b.locator('#party [data-character]').first().click();
  }
  await b.locator('.sheet-checks').waitFor();
  assert.equal(actions.length,lostCreation?2:1);assert.equal(actions[0].type,'create_character');assert.equal(await b.locator('#characterForm').count(),0);
  if(!delayedCreator){assert.equal(await b.locator('#creatorContinue').textContent(),'Volver a la mesa');assert.equal(await b.locator('#showCharacterOnBoard').count(),0,'The first creation step keeps its single continuation choice')}
  let state=await (await guest.request.get(url+'/api/state',{headers:{Authorization:'Bearer '+player}})).json();
  const character=state.state.characters[0];assert.equal(character.damage,'2d6+6');assert.equal(character.ac,16);assert.equal(character.maxHp,16);assert.ok(character.creation);
  await b.locator('.sheet-free-roll > summary').click();await b.locator('[data-sheet-selection]').selectOption('0');
  await b.locator('[data-check-key=str]').click();await b.waitForFunction(()=>snapshot.state.messages.at(-1).check?.total===16);
  await b.locator('#closeModal').click();await b.reload();await b.locator('.party-person').click();await b.locator('.sheet-checks').waitFor();
  if(process.env.TEST_SHOW_CHARACTER_ON_BOARD==='1'){
   assert.equal(await b.locator('#showCharacterOnBoard').count(),1,'An existing character sheet should provide a local way back to its token');
   const requests=[],observe=request=>{if(new URL(request.url()).pathname.startsWith('/api/'))requests.push(request.url())};b.on('request',observe);
   for(const [width,height] of [[1280,900],[390,844]]){
    await b.locator('#closeModal').click();await b.setViewportSize({width,height});if(await b.locator('[data-tab=board]').isVisible())await b.locator('[data-tab=board]').click();await b.locator('.board-scroll').evaluate(element=>{element.scrollLeft=element.scrollWidth;element.scrollTop=element.scrollHeight});
    const before=await b.evaluate(()=>({state:structuredClone(snapshot.state),version:snapshot.version,selected:document.querySelector('#boardCharacter').value,speaker:document.querySelector('#speaker').value})),count=actions.length;await b.locator('#party [data-character]').first().click();await b.locator('#showCharacterOnBoard').focus();await b.keyboard.press('Enter');assert.equal(await b.locator('#modal').evaluate(element=>element.open),false);assert.equal(await b.locator('#grid .cell:focus').getAttribute('data-token-id'),character.id);assert.equal(await b.locator('#grid .located-token').count(),1);
    assert.ok(await b.locator('#grid .cell:focus').evaluate(element=>{const cell=element.getBoundingClientRect(),frame=document.querySelector('.board-scroll').getBoundingClientRect(),panel=document.querySelector('#board').getBoundingClientRect();return cell.left>=Math.max(0,frame.left,panel.left)&&cell.right<=Math.min(innerWidth,frame.right,panel.right)&&cell.top>=Math.max(0,frame.top,panel.top)&&cell.bottom<=Math.min(innerHeight,frame.bottom,panel.bottom)}),'The token must be visible inside the board after revealing it');assert.deepEqual(await b.evaluate(()=>({state:structuredClone(snapshot.state),version:snapshot.version,selected:document.querySelector('#boardCharacter').value,speaker:document.querySelector('#speaker').value})),before);assert.equal(actions.length,count);await b.locator('#tool').focus();assert.equal(await b.locator('.located-token').count(),0);await b.locator('#party [data-character]').first().click();
   }
   await b.setViewportSize({width:1280,height:900});
   b.off('request',observe);assert.equal(requests.length,0,'Revealing a loaded token must stay entirely local');
  }
  assert.equal(await b.locator('#advancedCharacterEdit').count(),1);
  assert.equal(await b.locator('#advancedCharacterEdit').isHidden(),true);const beforeCorrection=actions.length;await b.locator('#characterAdvanced > summary').focus();await b.keyboard.press('Enter');assert.equal(await b.locator('#advancedCharacterEdit').isVisible(),true);assert.match(await b.locator('#advancedEditHint').textContent(),/excepción/);await b.keyboard.press('Enter');assert.equal(actions.length,beforeCorrection);
  assert.equal(await b.locator('[data-sheet-check]').isVisible(),false);
  await b.setViewportSize({width:390,height:900});
  assert.equal(await b.locator('#modal').evaluate(el=>el.scrollWidth<=el.clientWidth),true);
  await b.screenshot({path:'.deps/character-sheet-guided-mobile.png',fullPage:true});
  await b.locator('#closeModal').click();await b.setViewportSize({width:1280,height:900});
  // A host can create a usable opposing fighter through the same wizard.
  await a.goto(url);await a.locator('#app').waitFor({state:'visible'});await a.locator('#addCharacter').click();
  await a.locator('#creatorName').fill('Bandido');assert.equal(await a.locator('#creatorEnemy').isHidden(),true);const beforeAdvanced=await a.evaluate(()=>snapshot.version);await a.locator('#creatorAdvanced summary').focus();await a.keyboard.press('Enter');assert.equal(await a.evaluate(()=>snapshot.version),beforeAdvanced);await a.locator('#creatorEnemy').check();
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
  assert.match(await b.locator('#playGuidanceText').textContent(),/Es tu turno/);
  const beforeTurnGuide=await b.evaluate(()=>snapshot.version);await b.locator('#playGuidanceAction').click();
  assert.equal(await b.locator('#boardCharacter').inputValue(),character.id);
  assert.equal(await b.evaluate(()=>snapshot.version),beforeTurnGuide);
  await b.locator('#attackButton').click();await b.waitForFunction(()=>snapshot.state.board.spent[snapshot.state.characters[0].id]?.standard);
  state=await (await guest.request.get(url+'/api/state',{headers:{Authorization:'Bearer '+player}})).json();
  assert.ok(state.state.characters[1].hp<state.state.characters[1].maxHp);
  const beforeCombatSheet=actions.length;await b.locator('#party [data-character="'+character.id+'"]').click();await b.locator('#characterAdvanced > summary').focus();await b.keyboard.press('Enter');assert.equal(await b.locator('#advancedCharacterEdit').isDisabled(),true);assert.match(await b.locator('#advancedEditHint').textContent(),/durante el combate/);assert.equal(actions.length,beforeCombatSheet);
  if(process.env.TEST_SHOW_CHARACTER_ON_BOARD==='1'){await b.locator('#closeModal').click();await b.setViewportSize({width:390,height:844});await b.locator('[data-tab=board]').click();await b.locator('.board-scroll').evaluate(element=>{element.scrollLeft=element.scrollWidth;element.scrollTop=element.scrollHeight});const target=state.state.characters[1],before=await b.evaluate(()=>({state:structuredClone(snapshot.state),version:snapshot.version,selected:document.querySelector('#boardCharacter').value}));await b.locator('#party [data-character="'+target.id+'"]').click();await b.locator('#showCharacterOnBoard').tap();assert.equal(await b.locator('#grid .cell:focus').getAttribute('data-token-id'),target.id);assert.deepEqual(await b.evaluate(()=>({state:structuredClone(snapshot.state),version:snapshot.version,selected:document.querySelector('#boardCharacter').value})),before);assert.equal(await b.locator('#boardCharacter').inputValue(),character.id);assert.equal(actions.length,beforeCombatSheet)}
  assert.deepEqual(errors,[]);console.log('OK: zero manual statistics; guided creation, local invalid-budget preview, one save, sheet roll, reload, mobile wizard, generated adversary and real engine attack. No AI.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
