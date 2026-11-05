const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const seed=spawn(path.resolve('.venv/Scripts/python.exe'),['-c',"import json;from pathlib import Path;from test_target_objective_plan import TargetObjectivePlanTests;f=TargetObjectivePlanTests();f.setUp();Path('.deps/pending-recovery-fixture.json').write_text(json.dumps({'format':'cronicas-1','title':'Recuperación - apertura simulada','state':f.state},ensure_ascii=False),encoding='utf-8')"],{stdio:'inherit'});
 await new Promise((resolve,reject)=>seed.once('exit',code=>code===0?resolve():reject(Error('Fixture generation failed'))));
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_RULE_PACK_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Recuperación de envío',ruleset:'rule-pack'}})).json();
  const headers={Authorization:'Bearer '+room.token};let current=await (await context.request.get(url+'/api/state',{headers})).json();
  const imported=await context.request.post(url+'/api/action',{headers,data:{id:crypto.randomUUID(),version:current.version,type:'import',campaign:require('./.deps/pending-recovery-fixture.json')}});assert.equal(imported.status(),200);
  await context.addInitScript(t=>localStorage.setItem('cronicas-token',t),room.token);
  const page=await context.newPage(),actions=[],errors=[];let interrupt=true;
  page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(request.url().endsWith('/api/action'))actions.push(request.postDataJSON())});
  await page.route('**/api/action',async route=>{
   if(interrupt&&route.request().postDataJSON().type==='resolve_pack_request'){interrupt=false;return route.abort('connectionreset')}
   await route.continue();
  });
  await page.goto(url);await page.locator('#packTargetChoices > summary').click();
  await page.locator('#packTargetChoice [name=action]').selectOption('contest');await page.locator('#packTargetChoice [name=target]').selectOption('a'.repeat(24));
  await page.locator('#packTargetChoice button').click();await page.locator('#packStoryResolve button.primary').click();
  await page.waitForFunction(()=>!busy&&localStorage.getItem('cronicas-pending')!==null);
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('cronicas-pending')).body);
  current=await (await context.request.get(url+'/api/state',{headers})).json();
  const ooc=await context.request.post(url+'/api/action',{headers,data:{id:crypto.randomUUID(),version:current.version,type:'talk_pack_adventure',character:saved.character||current.state.narrativeView.pending.character,mode:'ooc',text:'Mensaje de otra pestaña.'}});assert.equal(ooc.status(),200);
  await page.reload();await page.waitForFunction(()=>snapshot?.state.narrativeView.continuation!==null&&localStorage.getItem('cronicas-pending')===null);
  const resolutions=actions.filter(action=>action.type==='resolve_pack_request');assert.equal(resolutions.length,3);
  assert.equal(resolutions[0].id,resolutions[1].id);assert.notEqual(resolutions[1].id,resolutions[2].id);
  assert.equal(resolutions[2].version,resolutions[1].version+1);assert.equal(resolutions[2].request,saved.request);
  assert.equal(actions.filter(action=>action.type==='continue_pack_adventure').length,0);
  const exported=await (await context.request.post(url+'/api/export',{headers,data:{}})).json();
  assert.equal(exported.state.targetResolutions.length,1);assert.equal(exported.state.characters[0].sheet.fields.energy,2);
  assert.ok(exported.state.messages.some(message=>message.text==='Mensaje de otra pestaña.'));
  assert.deepEqual(errors,[]);console.log('Pending recovery browser passed: interrupted submission, intervening OOC, original retry then one current-version recovery, one resolution, no narrative inference. Backend tests separately verify durable original dice.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
