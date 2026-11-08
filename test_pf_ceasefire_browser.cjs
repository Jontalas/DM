const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_PF_ENCOUNTER_VERSION:'1.8.0',TEST_PF_CEASEFIRE_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  for(const speaksGoblin of [true,false]){
   const context=await browser.newContext({hasTouch:true}),page=await context.newPage(),actions=[],errors=[];
   page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Resolver el paso');await page.locator('#createForm button').click();
   await page.waitForFunction(()=>snapshot?.state&&!busy);
   // Legal builder input through the normal action API, never edited statistics.
   await page.evaluate(async speaks=>{await act('create_character',{choices:{name:'Aria',race:'human',class:'fighter',level:1,abilities:speaks?[16,14,14,12,10,8]:[16,14,14,10,12,8],bonus:0,weapon:'longsword',armor:'chainshirt',shield:'heavy',favored:'hp',feats:['focus','initiative','toughness'],skills:speaks?['climb','intimidate','perception','swim']:['climb','intimidate','perception'],languages:speaks?['Goblin']:[]}})},speaksGoblin);
   await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();await page.locator('#pfEncounterCombat').click();
   await page.waitForFunction(()=>snapshot.state.board.active&&!busy);await page.locator('#attackButton').click();
   await page.waitForFunction(()=>snapshot.state.characters[1].hp===2&&!busy);await page.locator('[data-tab=story]').click();
   await page.locator('#pfAcceptCeasefire').waitFor();const before=await page.evaluate(()=>structuredClone(snapshot.state));
   if(!speaksGoblin){assert.equal(await page.locator('#pfAcceptCeasefire').isEnabled(),false);assert.match(await page.locator('#pfCeasefireHint').textContent(),/idioma goblin/);}
   else{
    const count=actions.length;await page.locator('#playGuidanceAction').focus();await page.keyboard.press('Enter');assert.equal(await page.locator('#pfAcceptCeasefire').evaluate(e=>e===document.activeElement),true);assert.equal(actions.length,count);
    await page.setViewportSize({width:390,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:'.deps/pf-ceasefire-mobile.png',fullPage:true});await page.locator('#pfAcceptCeasefire').tap();
    await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='agreement'&&!busy);assert.equal(actions.length,count+1);
    assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),before.characters);assert.equal(await page.evaluate(()=>snapshot.state.worldTime),before.worldTime);
    assert.equal(await page.evaluate(()=>snapshot.state.board.active),false);await page.reload();await page.waitForFunction(()=>snapshot?.state.pfEncounter.phase==='agreement'&&!busy);
    await page.locator('#pfContinueScene').click();await page.waitForFunction(()=>snapshot.state.boardScenes?.current==='patio'&&!busy);
    assert.equal(await page.evaluate(()=>snapshot.state.characters[1].hp),2);
   }
   assert.deepEqual(errors,[]);await context.close();
  }
  console.log('Ceasefire browser verified: legal builder API, organic wound, language limit, keyboard/mobile/touch, conserved wounds, reload and onward route; no provider.');
 }finally{await browser?.close();fixture.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});
