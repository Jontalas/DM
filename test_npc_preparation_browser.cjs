const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const seed=spawn(path.resolve('.venv/Scripts/python.exe'),['-c',"import json;from pathlib import Path;from test_character_builder import choices;Path('.deps/npc-player-choices.json').write_text(json.dumps(choices()),encoding='utf-8')"],{stdio:'inherit'});
 await new Promise((resolve,reject)=>seed.once('exit',code=>code===0?resolve():reject(Error('Player fixture failed'))));
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'PNJ verificado'}})).json();
  const headers={Authorization:'Bearer '+room.token};
  async function action(type,data){const current=await (await context.request.get(url+'/api/state',{headers})).json();const response=await context.request.post(url+'/api/action',{headers,data:{id:crypto.randomUUID(),version:current.version,type,...data}});assert.equal(response.status(),200)}
  await action('create_character',{choices:require('./.deps/npc-player-choices.json')});await action('create_npc',{template:'pf1-goblin-warrior-1',name:'Vigía <norte>'});
  const current=await (await context.request.get(url+'/api/state',{headers})).json(),npc=current.state.characters.find(character=>character.npcCreation);
  await context.addInitScript(token=>localStorage.setItem('cronicas-token',token),room.token);
  const page=await context.newPage(),actions=[],errors=[];page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(request.url().endsWith('/api/action'))actions.push(request.postDataJSON())});
  await page.goto(url);assert.match(await page.locator('#party').textContent(),/Director de la aventura/);
  await page.locator('[data-character="'+npc.id+'"]').first().click();await page.locator('[data-npc-provenance]').waitFor();
  assert.match(await page.locator('[data-npc-provenance]').textContent(),/visión en la oscuridad/i);
  assert.equal(await page.locator('#characterForm [name=owner]').inputValue(),'director');assert.equal(actions.length,0);
  await page.locator('#characterForm [name=hp]').fill('6');await page.locator('#characterForm button.primary').click();
  await page.waitForFunction(()=>snapshot.state.characters.some(character=>character.npcCreation?.manualOverride));assert.equal(actions.length,1);
  await page.locator('[data-character="'+npc.id+'"]').first().click();assert.match(await page.locator('[data-npc-provenance]').textContent(),/corrección excepcional/);
  assert.equal(await page.locator('#characterForm [name=owner]').inputValue(),'director');await page.locator('#closeModal').click();
  const guest=await (await context.request.post(url+'/api/join',{data:{name:'Luis',invite:current.invite}})).json(),other=await browser.newContext();
  await other.addInitScript(token=>localStorage.setItem('cronicas-token',token),guest.token);const spectator=await other.newPage();await spectator.goto(url);
  await spectator.locator('[data-character="'+npc.id+'"]').first().click();assert.equal(await spectator.locator('#characterForm button.primary').isDisabled(),true);
  await page.setViewportSize({width:390,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:'.deps/npc-preparation-mobile.png',fullPage:false});assert.deepEqual(errors,[]);
  console.log('NPC preparation browser passed: source coverage and director owner, escaped name, no actions on consultation, explicit manual correction retained, guest read-only, mobile. Preparation API only; no autonomous encounter advertised.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
