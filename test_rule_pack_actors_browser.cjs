const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const seed=spawn(path.resolve('.venv/Scripts/python.exe'),['-c',"import json;from pathlib import Path;from test_rule_pack_actors import ActorCampaignTests;f=ActorCampaignTests();f.setUp();Path('.deps/actor-browser-fixture.json').write_text(json.dumps({'format':'cronicas-1','title':'Actores privados - apertura simulada','state':f.state},ensure_ascii=False),encoding='utf-8')"],{stdio:'inherit'});
 await new Promise((resolve,reject)=>seed.once('exit',c=>c===0?resolve():reject(Error('Actor fixture failed'))));
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_RULE_PACK_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Actor views',ruleset:'rule-pack'}})).json();
  const headers={Authorization:'Bearer '+room.token};
  async function action(type,data){const state=await (await context.request.get(url+'/api/state',{headers})).json();const r=await context.request.post(url+'/api/action',{headers,data:{id:crypto.randomUUID(),version:state.version,type,...data}});assert.equal(r.status(),200);}
  const campaign=require('./.deps/actor-browser-fixture.json');await action('import',{campaign});
  for(const [actor,npc] of [['a'.repeat(24),'arda'],['b'.repeat(24),'sombra']])await action('create_pack_actor',{actor,npc,profile:'support',stages:[{inputs:{},physical:{}}],publicFields:['energy'],policy:'provided-profile'});
  const state=await (await context.request.get(url+'/api/state',{headers})).json(),guest=await (await context.request.post(url+'/api/join',{data:{name:'Luis',invite:state.invite}})).json();
  const errors=[],actions=[];
  for(const [role,token] of [['host',room.token],['guest',guest.token]]){
   const view=await browser.newContext();await view.addInitScript(t=>localStorage.setItem('cronicas-token',t),token);const page=await view.newPage();
   page.on('pageerror',e=>errors.push(e.stack));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#packKnownNpcs > summary').click();
   assert.equal(await page.locator('.pack-shared-actor-fields').count(),1);assert.match(await page.locator('.pack-shared-actor-fields').textContent(),/Energía2/);
   assert.equal(await page.evaluate(()=>Object.hasOwn(snapshot.state,'actors')),false);
   assert.ok(!(await page.evaluate(()=>JSON.stringify(snapshot))).includes('PRIVATE-ACTOR-NAME'));
   assert.deepEqual(await page.evaluate(()=>Object.keys(snapshot.state.actorViews[0].fields)),['energy']);
   await page.locator('#packKnownNpcs > summary').click();await page.locator('#packKnownNpcs > summary').click();
   if(role==='host'){await page.setViewportSize({width:390,height:1000});await page.locator('#packKnownNpcs').scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/actor-fields-mobile.png',fullPage:false});}
   await view.close();
  }
  assert.equal(actions.length,0);assert.deepEqual(errors,[]);console.log('Actor browser passed: real local API preparation, known public field only, hidden actor absent, host/guest/mobile, consultation zero actions. Opening simulated.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
