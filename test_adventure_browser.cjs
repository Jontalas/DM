// Isolated provider fixture, not a real AI quality evaluation.
const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{
  env:{...process.env,TEST_ADVENTURE_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const host=await browser.newContext(),guest=await browser.newContext();
  for(const context of [host,guest])await context.route('**/api/status',async route=>{
   const response=await route.fetch();await route.fulfill({json:{...await response.json(),aiConfigured:true}});
  });
  const token=(await (await host.request.post(url+'/api/create',{data:{player:'Ana',title:'Adventure fixture',goal:'Investigar las luces'}})).json()).token;
  const headers={Authorization:'Bearer '+token};
  const catalog=require('./static/creation-catalog.json');
  const choices={...catalog.presets.guardian,name:'Aria',race:'human',class:'fighter',level:1,favored:'hp',feats:['focus','initiative','toughness'],skills:['climb','intimidate','perception'],languages:[]};
  let room=await (await host.request.get(url+'/api/state',{headers})).json();
  const player=(await (await guest.request.post(url+'/api/join',{data:{name:'Luis',invite:room.invite}})).json()).token;
  room=await (await host.request.get(url+'/api/state',{headers})).json();
  assert.ok((await host.request.post(url+'/api/action',{headers,data:{id:'fixture-hero',version:room.version,type:'create_character',choices}})).ok());
  await host.addInitScript(t=>localStorage.setItem('cronicas-token',t),token);
  await guest.addInitScript(t=>localStorage.setItem('cronicas-token',t),player);
  const a=await host.newPage(),b=await guest.newPage(),errors=[],actions=[];
  for(const page of [a,b])page.on('pageerror',error=>errors.push(error.message));
  a.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await a.goto(url);await a.locator('#beginAdventure').waitFor();
  await a.locator('#beginAdventure').click();await a.locator('#adventureForm').waitFor();
  assert.equal(actions.length,0);
  await a.locator('#adventureForm [name=premise]').fill('Investigar las luces del molino');
  await a.locator('#adventureForm button').click();await a.locator('#modal').waitFor({state:'hidden'});
  assert.equal(actions.length,1);assert.equal(actions[0].type,'start_adventure');
  await a.locator('nav [data-tab=journal]').click();
  assert.match(await a.locator('#adventureSummary').textContent(),/puerta sigue cerrada/);
  assert.equal(await a.locator('#directorMemoryDetails').isVisible(),true);
  await b.goto(url);await b.locator('#app').waitFor({state:'visible'});
  await b.locator('nav [data-tab=journal]').click();
  assert.equal(await b.locator('#directorMemoryDetails').isVisible(),false);
  const guestState=await (await guest.request.get(url+'/api/state',{headers:{Authorization:'Bearer '+player}})).json();
  assert.ok(!JSON.stringify(guestState).includes('bajo la escalera'));
  await a.locator('nav [data-tab=story]').click();
  await a.locator('#message').fill('Intento abrir la puerta');await a.locator('#send').click();
  await a.locator('[data-resolve-check]').waitFor();
  assert.equal(await a.locator('#continueAdventure').isVisible(),false);
  await a.locator('[data-resolve-check]').click();await a.locator('#continueAdventure').waitFor();
  await a.locator('#continueAdventure').click();
  await a.waitForFunction(()=>snapshot.state.adventure.revision===2);
  assert.equal(await a.locator('#continueAdventure').isVisible(),false);
  assert.deepEqual(actions.map(item=>item.type),['start_adventure','talk','check','continue_adventure']);
  await a.reload();await a.locator('#app').waitFor({state:'visible'});
  assert.equal(await a.locator('#beginAdventure').count(),0);
  await a.locator('nav [data-tab=journal]').click();
  assert.match(await a.locator('#adventureSummary').textContent(),/superar la prueba/);
  await a.setViewportSize({width:390,height:844});
  assert.ok(await a.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await a.screenshot({path:'.deps/adventure-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('OK: start, memory, secret isolation, check-to-narration, no duplicate calls, reload and mobile. Provider simulated.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
