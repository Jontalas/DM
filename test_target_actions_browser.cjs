const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const seed=spawn(path.resolve('.venv/Scripts/python.exe'),['-c',"import json;from pathlib import Path;from test_target_context import AbstractTargetContextTests;f=AbstractTargetContextTests();f.setUp();f.state['actors'][0]['publicFields']=['energy','exhausted'];Path('.deps/target-action-browser-fixture.json').write_text(json.dumps({'format':'cronicas-1','title':'Acciones abstractas - apertura simulada','state':f.state},ensure_ascii=False),encoding='utf-8')"],{stdio:'inherit'});
 await new Promise((resolve,reject)=>seed.once('exit',c=>c===0?resolve():reject(Error('Target-action fixture failed'))));
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_RULE_PACK_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Target action UI',ruleset:'rule-pack'}})).json();
  const headers={Authorization:'Bearer '+room.token},current=await (await context.request.get(url+'/api/state',{headers})).json();
  const imported=await context.request.post(url+'/api/action',{headers,data:{id:crypto.randomUUID(),version:current.version,type:'import',campaign:require('./.deps/target-action-browser-fixture.json')}});assert.equal(imported.status(),200);
  await context.addInitScript(t=>localStorage.setItem('cronicas-token',t),room.token);
  const page=await context.newPage(),errors=[],actions=[];
  page.on('pageerror',e=>errors.push(e.stack));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#packTargetChoices > summary').click();
  await page.locator('#packTargetChoice [name=action]').selectOption('contest');
  assert.equal(await page.locator('#packTargetChoice [name=target] option').count(),2);
  await page.locator('#packTargetChoice [name=target]').selectOption('a'.repeat(24));assert.equal(actions.length,0);
  await page.evaluate(()=>refresh(true));assert.equal(await page.locator('#packTargetChoice [name=target]').inputValue(),'a'.repeat(24));assert.equal(actions.length,0);
  await page.locator('#packTargetChoice button').click();await page.locator('#packStoryResolve').waitFor();
  assert.deepEqual(actions.map(a=>a.type),['request_pack_target']);
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.energy),3);
  assert.equal(await page.evaluate(()=>snapshot.state.narrativeView.pending.targetBinding.npc),'arda');
  await page.locator('#packStoryResolve summary').click();await page.locator('#packStoryResolve [name=dice0]').fill('3, 4');
  await page.locator('#packStoryResolve button.primary').click();await page.waitForFunction(()=>snapshot.state.narrativeView.revision===2&&!snapshot.state.narrativeView.continuation);
  assert.deepEqual(actions.map(a=>a.type),['request_pack_target','resolve_pack_request','continue_pack_adventure']);
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.energy),2);
  assert.equal(await page.evaluate(()=>snapshot.state.actorViews[0].fields.energy.value),1);
  assert.equal(await page.evaluate(()=>Object.hasOwn(snapshot.state,'targetResolutions')),false);
  assert.match(await page.locator('[data-pack-target-result]').textContent(),/Arda/);
  const before=actions.length;await page.locator('#packKnownNpcs > summary').click();assert.equal(actions.length,before);
  await page.setViewportSize({width:390,height:1000});await page.locator('[data-pack-target-result]').scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/target-actions-mobile.png',fullPage:false});
  assert.deepEqual(errors,[]);console.log('Target action browser passed: explicit known NPC choice, local draft, zero inference for request, physical two-sheet resolution, one simulated continuation, private proof hidden, mobile. Abstract scene only.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
