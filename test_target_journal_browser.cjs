const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const seed=spawn(path.resolve('.venv/Scripts/python.exe'),['-c',"import json;from pathlib import Path;from test_target_journal import TargetJournalTests;f=TargetJournalTests();f.setUp();s=f.resolve(f.state,[3,4]);s['actors'][0]['publicFields']=['energy'];s['narrative']['npcs'][0]['name']='Arda <vecina>';s['narrative']['continuation']={'character':f.cid,'message':len(s['messages'])-1};Path('.deps/target-browser-fixture.json').write_text(json.dumps({'format':'cronicas-1','title':'Resolucion preparada - apertura simulada','state':s},ensure_ascii=False),encoding='utf-8')"],{stdio:'inherit'});
 await new Promise((resolve,reject)=>seed.once('exit',c=>c===0?resolve():reject(Error('Journal fixture failed'))));
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_RULE_PACK_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Journal projection',ruleset:'rule-pack'}})).json();
  const headers={Authorization:'Bearer '+room.token},current=await (await context.request.get(url+'/api/state',{headers})).json();
  const imported=await context.request.post(url+'/api/action',{headers,data:{id:crypto.randomUUID(),version:current.version,type:'import',campaign:require('./.deps/target-browser-fixture.json')}});assert.equal(imported.status(),200);
  await context.addInitScript(t=>localStorage.setItem('cronicas-token',t),room.token);
  const page=await context.newPage(),errors=[],actions=[];
  page.on('pageerror',e=>errors.push(e.stack));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('[data-pack-target-result]').waitFor();
  assert.match(await page.locator('[data-pack-target-result]').textContent(),/Arda <vecina>/);assert.equal(await page.locator('[data-pack-target-result] vecina').count(),0);
  assert.equal(await page.evaluate(()=>Object.hasOwn(snapshot.state,'targetResolutions')),false);
  assert.equal(await page.evaluate(()=>Object.hasOwn(snapshot.state,'actors')),false);
  assert.equal(await page.evaluate(()=>Object.hasOwn(snapshot.state.messages.at(-1).trace,'target')),false);
  assert.equal(await page.locator('[data-pack-action=contest]').count(),0);
  await page.locator('#packKnownNpcs > summary').click();assert.match(await page.locator('.pack-shared-actor-fields').textContent(),/Energía1/);assert.equal(actions.length,0);
  await page.locator('#packStoryContinue').click();await page.waitForFunction(()=>snapshot.state.narrativeView.revision===2);
  assert.equal(actions.length,1);assert.equal(actions[0].type,'continue_pack_adventure');assert.match(await page.locator('.pack-story-message').last().textContent(),/datos compartidos/);
  const invite=await page.evaluate(()=>snapshot.invite),guest=await (await context.request.post(url+'/api/join',{data:{name:'Luis',invite}})).json();
  const guestContext=await browser.newContext();await guestContext.addInitScript(t=>localStorage.setItem('cronicas-token',t),guest.token);const guestPage=await guestContext.newPage();
  guestPage.on('pageerror',e=>errors.push(e.stack));await guestPage.goto(url);await guestPage.locator('[data-pack-target-result]').waitFor();
  assert.equal(await guestPage.evaluate(()=>Object.hasOwn(snapshot.state,'targetResolutions')),false);
  await page.setViewportSize({width:390,height:1000});await page.locator('[data-pack-target-result]').scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/target-history-mobile.png',fullPage:false});
  assert.deepEqual(errors,[]);console.log('Target journal browser passed: imported deterministic resolution, named target escaped, private proof/actor absent, shared field, one simulated continuation, guest/mobile. Target actions remain unavailable.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
