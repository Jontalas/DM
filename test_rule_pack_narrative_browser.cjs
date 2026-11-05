const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_RULE_PACK_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'El farol perdido',ruleset:'rule-pack',goal:'Investigar un farol perdido'}})).json();
  await context.addInitScript(t=>{if(!localStorage.getItem('cronicas-token'))localStorage.setItem('cronicas-token',t)},room.token);
  const page=await context.newPage(),actions=[],errors=[];
  page.on('pageerror',e=>errors.push(e.stack));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  const discoveryContract=process.env.TEST_DISCOVERIES==='1',resultContract=discoveryContract||process.env.TEST_ACTION_RESULT_CONTRACT==='1';
  await page.goto(url);await page.locator('#packFile').setInputFiles(resultContract?'test_fixtures/rule_packs/original-narrative-results-example.json':'test_fixtures/rule_packs/live-lantern-example.json');
  await page.locator('#packInstall [name=use]').check();await page.locator('#packInstall button').click();
  await page.locator('#packCreate [name=name]').fill('Aria');await page.locator('#packCreate button').click();
  await page.locator('#packStoryStart summary').click();
  await page.locator('#packStoryStart [name=sourceTitle]').fill('El farol — aventura propia');
  const originalSource='Arda custodia el archivo junto al farol.\r\nPRIVATE-ADVENTURE-SOURCE: una carta secreta espera bajo el suelo.\r\n';
  await page.locator('#packAdventureFile').setInputFiles({name:'aventura-propia.txt',mimeType:'text/plain',buffer:Buffer.from(originalSource,'utf8')});
  await page.waitForFunction(()=>document.querySelector('#packStoryStart [name=sourceText]').value.includes('PRIVATE-ADVENTURE-SOURCE'));
  await page.locator('#packStoryStart [name=sourceUse]').check();
  const beforeSource=actions.length;await page.evaluate(()=>refresh(true));
  assert.match(await page.locator('#packStoryStart [name=sourceText]').inputValue(),/PRIVATE-ADVENTURE-SOURCE/);assert.equal(actions.length,beforeSource);
  await page.locator('#packStoryStart button').click();await page.locator('#packStoryTalk').waitFor();
  const sourceExport=await (await context.request.post(url+'/api/export',{headers:{Authorization:'Bearer '+room.token},data:{}})).json();
  assert.equal(sourceExport.state.adventureSource.text,originalSource);
  assert.match(await page.locator('.pack-source-note').textContent(),/El farol/);
  assert.ok(!(await page.evaluate(()=>JSON.stringify(snapshot))).includes('PRIVATE-ADVENTURE-SOURCE'));
  assert.equal(await page.evaluate(()=>snapshot.state.narrativeView.revision),1);
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.energy),3);
  assert.ok(!(await page.evaluate(()=>JSON.stringify(snapshot))).includes('PRIVATE-DIRECTOR'));
  assert.equal(await page.locator('[data-pack-action]').count(),0);
  if(discoveryContract){
   const source=originalSource,text='una carta secreta espera bajo el suelo.',start=source.indexOf(text);
   const current=await page.evaluate(()=>snapshot);
   const configured=await context.request.post(url+'/api/action',{headers:{Authorization:'Bearer '+room.token},data:{id:'prepare-discovery-browser',version:current.version,type:'prepare_pack_discoveries',policy:'provided-adventure',definitions:[{id:'carta',objective:'marca',field:'success',start,end:start+text.length,text}]}});
   assert.equal(configured.status(),200);await page.evaluate(()=>refresh(true));
   await page.locator('#packDiscoveries > summary').click();assert.equal(await page.locator('[data-pack-discovery]').count(),0);
   assert.ok(!(await page.evaluate(()=>JSON.stringify(snapshot))).includes(text));
  }
  const count=actions.length;
  await page.locator('#packKnownNpcs > summary').click();
  assert.match(await page.locator('#packKnownNpcs').textContent(),/Arda <archivera>/);
  assert.equal(await page.locator('#packKnownNpcs img').count(),0);
  assert.ok(!(await page.evaluate(()=>JSON.stringify(snapshot))).includes('PRIVATE-NPC'));
  await page.evaluate(()=>refresh(true));assert.equal(await page.locator('#packKnownNpcs').getAttribute('open'),'');
  assert.equal(actions.length,count);
  await page.locator('#packWorld > summary').click();
  assert.match(await page.locator('#packWorld').textContent(),/Archivo <antiguo>/);
  assert.match(await page.locator('#packWorld').textContent(),/Arda custodia este archivo/);
  assert.equal(await page.locator('[data-pack-place]').count(),1);
  assert.ok(!(await page.evaluate(()=>JSON.stringify(snapshot))).includes('PRIVATE-WORLD'));
  assert.equal(actions.length,count);
  await page.locator('#packObjectives > summary').click();
  assert.match(await page.locator('[data-pack-objective=marca]').textContent(),/Abierto/);
  assert.equal(await page.locator('[data-pack-objective]').count(),1);
  assert.ok(!(await page.evaluate(()=>JSON.stringify(snapshot))).includes('PRIVATE-OBJECTIVE'));
  assert.equal(actions.length,count);
  await page.locator('#packStoryTalk [name=text]').fill('Investigo el farol.');await page.evaluate(()=>refresh(true));
  assert.equal(await page.locator('#packStoryTalk [name=text]').inputValue(),'Investigo el farol.');assert.equal(actions.length,count);
  await page.locator('#packStoryTalk button').click();await page.locator('#packStoryResolve').waitFor();
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.energy),3);
  assert.match(await page.locator('.pack-story-message').last().textContent(),/Arda/);
  await page.locator('#packStoryResolve summary').click();await page.locator('#packStoryResolve [name=dice0]').fill('3, 4');
  const beforeDice=actions.length;await page.evaluate(()=>refresh(true));
  assert.equal(await page.locator('#packStoryResolve [name=dice0]').inputValue(),'3, 4');assert.equal(actions.length,beforeDice);
  let lost=false;
  await page.route('**/api/action',async route=>{
   if(!lost&&route.request().postDataJSON()?.type==='resolve_pack_request'){lost=true;await route.fetch();await route.abort('connectionfailed')}
   else await route.continue();
  });
  await page.locator('#packStoryResolve button.primary').click();
  await page.waitForFunction(()=>snapshot.state.characters[0].sheet.fields.energy===2&&localStorage.getItem('cronicas-pending'));
  const pending=await page.evaluate(()=>JSON.parse(localStorage.getItem('cronicas-pending')));
  await page.reload();await page.waitForFunction(()=>snapshot?.state.narrativeView.continuation&&!localStorage.getItem('cronicas-pending'));
  assert.equal(actions.at(-1).id,pending.body.id);
  assert.equal(actions.filter(a=>a.type==='continue_pack_adventure').length,0);
  assert.deepEqual(await page.evaluate(()=>snapshot.state.messages.find(m=>m.kind==='pack-action').trace.rolls.dice.values),[3,4]);
  assert.equal(await page.evaluate(()=>snapshot.state.narrativeView.objectives[0].status),'completed');
  if(discoveryContract){
   await page.locator('#packDiscoveries > summary').click();
   assert.match(await page.locator('[data-pack-discovery=carta]').textContent(),/carta secreta espera bajo el suelo/);
   const beforeDiscovery=actions.length;await page.evaluate(()=>refresh(true));
   assert.equal(await page.locator('#packDiscoveries').getAttribute('open'),'');assert.equal(actions.length,beforeDiscovery);
  }
  if(resultContract){
   assert.match(await page.locator('.pack-confirmed-results').textContent(),/Éxito: Sí/);
   assert.match(await page.locator('.pack-confirmed-results').textContent(),/Objetivo completado: Investigar la marca/);
   const beforeIntent=actions.length;await page.locator('.pack-confirmed-results summary').click();
   assert.match(await page.locator('.pack-confirmed-results').textContent(),/Investigo el farol/);assert.equal(actions.length,beforeIntent);
  }
  await page.locator('#packObjectives > summary').click();
  assert.match(await page.locator('[data-pack-objective=marca]').textContent(),/Completado/);
  const beforeEvidence=actions.length;await page.locator('[data-pack-objective=marca] summary').click();
  assert.match(await page.locator('[data-pack-objective=marca]').textContent(),/Éxito: Sí/);assert.equal(actions.length,beforeEvidence);
  await page.unroute('**/api/action');await page.locator('#packStoryContinue').click();
  await page.waitForFunction(()=>snapshot.state.narrativeView.revision===3);
  assert.match(await page.locator('.pack-story-message').last().textContent(),/resultado confirmado/);
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.total),7);
  const directorEvents=await page.evaluate(()=>snapshot.state.messages.filter(m=>m.kind==='pack-director').length);
  await page.locator('#packStoryTalk [name=mode]').selectOption('ooc');await page.locator('#packStoryTalk [name=text]').fill('Una pausa fuera de personaje.');
  await page.locator('#packStoryTalk button').click();await page.waitForFunction(()=>snapshot.state.messages.at(-1).mode==='ooc');
  assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.kind==='pack-director').length),directorEvents);
  await page.locator('#packStoryTalk [name=mode]').selectOption('action');await page.locator('#packStoryTalk [name=text]').fill('TEST_UNSUPPORTED: lanzo un conjuro.');
  await page.locator('#packStoryTalk button').click();await page.waitForFunction(()=>snapshot.state.narrativeView.revision===4);
  assert.equal(await page.locator('#packStoryResolve').count(),0);assert.match(await page.locator('.pack-story-message').last().textContent(),/Límite del motor/);
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.energy),2);
  // Normal confirmation chains resolution and the one necessary narration.
  await page.locator('#packStoryTalk [name=text]').fill('Investigo de nuevo el farol.');await page.locator('#packStoryTalk button').click();
  await page.locator('#packStoryResolve').waitFor();await page.locator('#packStoryResolve button.primary').click();
  await page.waitForFunction(()=>snapshot.state.characters[0].sheet.fields.energy===1&&snapshot.state.narrativeView.revision===6);
  assert.equal(actions.filter(a=>a.type==='continue_pack_adventure').length,2);
  await page.locator('#toast').waitFor({state:'hidden'});
  await page.setViewportSize({width:390,height:1000});await page.locator('#packStoryTalk').scrollIntoViewIfNeeded();
  await page.locator('#packKnownNpcs > summary').click();
  await page.locator('#packKnownNpcs').scrollIntoViewIfNeeded();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/rule-pack-narrative-mobile.png',fullPage:true});
  await page.locator('#packWorld').evaluate(el=>el.open=true);await page.locator('#packWorld').scrollIntoViewIfNeeded();
  await page.screenshot({path:'.deps/rule-pack-world-mobile.png',fullPage:true});
  const invite=await page.evaluate(()=>snapshot.invite),guest=await (await context.request.post(url+'/api/join',{data:{name:'Luis',invite}})).json();
  const guestContext=await browser.newContext();await guestContext.addInitScript(t=>localStorage.setItem('cronicas-token',t),guest.token);
  const guestPage=await guestContext.newPage();guestPage.on('pageerror',e=>errors.push(e.stack));await guestPage.goto(url);await guestPage.locator('#packCreate').waitFor();
  assert.ok(!(await guestPage.evaluate(()=>JSON.stringify(snapshot))).includes('PRIVATE-DIRECTOR'));
  assert.ok(!(await guestPage.evaluate(()=>JSON.stringify(snapshot))).includes('PRIVATE-NPC'));
  assert.ok(!(await guestPage.evaluate(()=>JSON.stringify(snapshot))).includes('PRIVATE-OBJECTIVE'));
  assert.ok(!(await guestPage.evaluate(()=>JSON.stringify(snapshot))).includes('PRIVATE-ADVENTURE-SOURCE'));
  assert.equal(await guestPage.locator('.pack-source-note').count(),0);
  assert.equal(await guestPage.evaluate(()=>snapshot.state.narrativeView.objectives[0].status),'completed');
  if(discoveryContract){
   await guestPage.locator('#packDiscoveries > summary').click();
   assert.match(await guestPage.locator('[data-pack-discovery=carta]').textContent(),/carta secreta espera bajo el suelo/);
  }
  await guestPage.locator('#packKnownNpcs > summary').click();
  assert.match(await guestPage.locator('#packKnownNpcs').textContent(),/Custodia el archivo/);
  assert.equal(await guestPage.locator('#packStoryTalk').count(),0);
  await guestPage.locator('#packCreate [name=name]').fill('Ivo');await guestPage.locator('#packCreate button').click();await guestPage.locator('#packStoryTalk').waitFor();
  await guestPage.locator('#packStoryTalk [name=mode]').selectOption('dialogue');await guestPage.locator('#packStoryTalk [name=text]').fill('Arda, ¿viste el farol?');
  await guestPage.locator('#packStoryTalk button').click();await guestPage.waitForFunction(()=>snapshot.state.narrativeView.revision===7);
  assert.equal(await guestPage.evaluate(()=>snapshot.state.characters[0].sheet.fields.energy),1);
  assert.equal(await guestPage.evaluate(()=>snapshot.state.narrativeView.pending),null);
  await guestContext.close();assert.deepEqual(errors,[]);
  console.log('Generic adventure browser passed: start, declaration, legal request, local edits, physical dice, lost response recovery, confirmed narration, normal automatic continuation, OOC, limitation, privacy, second player and mobile. Provider simulated.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
