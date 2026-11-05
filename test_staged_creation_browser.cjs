const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_RULE_PACK_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Creación por etapas',ruleset:'rule-pack'}})).json();
  await context.addInitScript(t=>localStorage.setItem('cronicas-token',t),room.token);
  const page=await context.newPage(),actions=[],errors=[];
  page.on('pageerror',e=>errors.push(e.stack));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#packFile').setInputFiles('test_fixtures/rule_packs/original-staged-creation-example.json');
  await page.locator('#packInstall [name=use]').check();await page.locator('#packInstall button').click();
  await page.locator('#packCreate [name=name]').fill('Aria');await page.locator('#packCreate button').click();await page.locator('#packAction').waitFor();
  const initial=await page.evaluate(()=>snapshot.state.characters[0]),die=initial.creation.steps[0].trace.rolls.aptitude.values[0];
  assert.equal(initial.creationProgress.complete,false);assert.equal(initial.creationProgress.next,'training');
  assert.equal(await page.locator('#packStoryStart').count(),0);assert.equal(await page.locator('[data-pack-action]').count(),0);
  assert.equal(Number(await page.locator('#packAction').getByLabel('Enfoque',{exact:true}).getAttribute('max')),Math.min(2,die));
  const before=actions.length;await page.locator('#closeModal').click();await page.reload();await page.locator('[data-pack-creation]').waitFor();
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].creation.steps[0].trace.rolls.aptitude.values[0]),die);
  await page.locator('[data-pack-creation]').click();assert.equal(actions.length,before);
  await page.locator('#packAction').getByRole('combobox',{name:/Oficio/}).selectOption('cronista');await page.locator('#packAction').getByLabel('Enfoque',{exact:true}).fill(String(Math.min(2,die)));
  await page.setViewportSize({width:390,height:1000});await page.screenshot({path:'.deps/staged-creation-mobile.png',fullPage:true});
  let lost=false;await page.route('**/api/action',async route=>{
   if(!lost&&route.request().postDataJSON()?.type==='advance_pack_creation'){lost=true;await route.fetch();await route.abort('connectionfailed')}
   else await route.continue();
  });
  await page.locator('#packAction button.primary').click();await page.waitForFunction(()=>localStorage.getItem('cronicas-pending'));
  await page.reload();await page.waitForFunction(()=>snapshot?.state.characters[0].creationProgress.complete&&!localStorage.getItem('cronicas-pending'));
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].creation.steps.length),2);
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.talent),die+Math.min(2,die));
  assert.equal(await page.locator('[data-pack-creation]').count(),0);assert.equal(await page.locator('[data-pack-action=explore]').count(),1);
  assert.equal(await page.locator('#packStoryStart').count(),1);
  const advances=actions.filter(a=>a.type==='advance_pack_creation');assert.equal(advances.length,2);assert.equal(advances[0].id,advances[1].id);
  await page.locator('[data-pack-character]').click();await page.locator('#modalContent summary').click();
  assert.match(await page.locator('#modalContent').textContent(),/Descubrir tu aptitud/);assert.match(await page.locator('#modalContent').textContent(),/Elegir tu formación/);
  assert.deepEqual(errors,[]);console.log('Staged creator browser passed: guided next step, previous dice/derived legal bound, reload, local consultation, lost confirmation replay, final playable character and mobile. No inference.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
