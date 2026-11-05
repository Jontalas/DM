const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_RULE_PACK_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Resultados confirmados',ruleset:'rule-pack'}})).json();
  await context.addInitScript(t=>localStorage.setItem('cronicas-token',t),room.token);
  const page=await context.newPage(),actions=[],errors=[];
  page.on('pageerror',e=>errors.push(e.stack));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  const targeted=process.env.TEST_TARGET_SHEETS==='1',profiles=targeted||process.env.TEST_CREATION_PROFILES==='1';
  await page.goto(url);await page.locator('#packFile').setInputFiles(targeted?'test_fixtures/rule_packs/original-target-sheets-example.json':profiles?'test_fixtures/rule_packs/original-creation-profiles-example.json':'test_fixtures/rule_packs/original-staged-results-example.json');
  await page.locator('#packInstall [name=use]').check();await page.locator('#packInstall button').click();
  await page.locator('#packCreate [name=name]').fill('Aria');await page.locator('#packCreate button').click();await page.locator('#packAction').waitFor();
  await page.locator('#packAction').getByRole('combobox',{name:/Oficio/}).selectOption('cronista');await page.locator('#packAction').getByLabel('Enfoque',{exact:true}).fill('0');
  await page.locator('#packAction button.primary').click();await page.waitForFunction(()=>snapshot.state.characters[0].creationProgress.complete);
  if(profiles)assert.equal(await page.locator('[data-pack-action=prepare-support]').count(),0);
  if(targeted)assert.equal(await page.locator('[data-pack-action=contest]').count(),0);
  for(const energy of [2,1]){
   await page.locator('[data-pack-action=explore]').click();await page.locator('#packAction summary').click();
   await page.locator('#packAction [name=dice0]').fill('3, 4');await page.locator('#packAction button.primary').click();
   await page.waitForFunction(expected=>snapshot.state.characters[0].sheet.fields.energy===expected,energy);
   assert.match(await page.locator('.pack-confirmed-results').last().textContent(),/Éxito: Sí/);
  }
  assert.equal(await page.locator('.pack-confirmed-results').count(),2);
  assert.equal(await page.evaluate(()=>Object.hasOwn(snapshot.state.messages.filter(m=>m.kind==='pack-action').at(-1).trace.changes,'success')),false);
  assert.equal(await page.evaluate(()=>snapshot.state.messages.filter(m=>m.kind==='pack-action').at(-1).trace.results.success),true);
  assert.equal(actions.filter(a=>['start_pack_adventure','talk_pack_adventure','continue_pack_adventure'].includes(a.type)).length,0);
  await page.setViewportSize({width:390,height:1000});await page.locator('.pack-confirmed-results').last().scrollIntoViewIfNeeded();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'.deps/action-results-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);console.log('Action results browser passed: staged creation, physical dice, repeated true output with no field delta, canonical result card, mobile and zero inference.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
