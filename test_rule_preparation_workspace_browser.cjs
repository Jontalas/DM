const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_RULE_PACK_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Manual por bloques',ruleset:'rule-pack'}})).json();
  await context.addInitScript(t=>{if(!localStorage.getItem('cronicas-token'))localStorage.setItem('cronicas-token',t)},room.token);
  const page=await context.newPage(),actions=[],errors=[];
  page.on('pageerror',e=>errors.push(e.stack));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#packPrepareOpen').waitFor();
  async function prepare(scope){
   await page.locator('#packPrepareOpen').click();
   const fields={title:'Reglas propias por bloques',edition:'Ejemplo original 1',scope,attribution:'Reglas originales para pruebas.',
    text:'Energía inicial 3. Un intento requiere energía positiva, gasta 1 y tira 2d6; 7–12 es éxito y 2–6 fallo. Al llegar a energía 0 se activa agotamiento. PRIVATE-SHARED-ORIGINAL'};
   for(const [name,value] of Object.entries(fields))await page.locator(`#packPrepare [name=${name}]`).fill(value);
   await page.locator('#packPrepare button[type=submit]').click();await page.locator('#modal').waitFor({state:'hidden'});
  }
  await prepare('TEST_DICE_BLOCK');const first=await page.evaluate(()=>snapshot.state.authoringWorkspace.latest);
  await prepare('TEST_EXHAUSTION_BLOCK');const second=await page.evaluate(()=>snapshot.state.authoringWorkspace.latest);
  assert.notEqual(first,second);assert.equal(await page.evaluate(()=>Object.keys(snapshot.state.authoringWorkspace.blocks).length),2);
  assert.equal(await page.evaluate(()=>Object.keys(snapshot.state.authoringWorkspace.texts).length),1);
  assert.equal(await page.evaluate(()=>Object.keys(snapshot.state.authoringWorkspace.sources).length),1);
  assert.equal(await page.evaluate(()=>snapshot.state.authoring),null);
  await page.reload();await page.locator('#packSavedBlocks summary').click();
  const writes=actions.length;
  await page.locator(`[data-prepared-block="${first}"]`).click();assert.match(await page.locator('#modalContent').textContent(),/1 ejemplos comprobados/);
  await page.locator('#modalContent summary').click();assert.match(await page.locator('.pack-source').textContent(),/PRIVATE-SHARED-ORIGINAL/);
  await page.locator('#closeModal').click();await page.locator(`[data-prepared-block="${second}"]`).click();
  assert.match(await page.locator('#modalContent').textContent(),/2 ejemplos comprobados/);assert.equal(actions.length,writes);
  await page.locator('#closeModal').click();await page.locator(`[data-prepared-block="${first}"]`).click();
  await page.locator('#packReviewPrepared').click();await page.locator('#packInstall [name=use]').check();await page.locator('#packInstall button').click();
  await page.locator('#packCreate').waitFor();assert.equal(await page.evaluate(()=>Object.keys(snapshot.state.package.document.triggers).length),0);
  await page.locator('#packPreparationReport').click();await page.locator('#packAddPrepared').click();
  await page.locator('#packComposePreview button').click();await page.locator('#packComposeInstall [name=use]').check();await page.locator('#packComposeInstall button').click();
  await page.locator('#modal').waitFor({state:'hidden'});
  await page.locator('#packCreate').waitFor();assert.equal(await page.evaluate(()=>snapshot.state.package.document.sources.length),1);
  assert.ok(await page.evaluate(()=>!!snapshot.state.package.document.triggers.exhaustion));
  await page.locator('#packCreate [name=name]').fill('Lúa');await page.locator('#packCreate button').click();
  for(let i=0;i<3;i++){await page.locator('[data-pack-action=attempt]').click();await page.locator('#packAction button').click();await page.locator('#modal').waitFor({state:'hidden'});}
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.exhausted),true);
  assert.equal(actions.filter(a=>a.type==='prepare_rule_pack').length,2);
  const invite=await page.evaluate(()=>snapshot.invite),guest=await (await context.request.post(url+'/api/join',{data:{name:'Luis',invite}})).json();
  const guestState=await (await context.request.get(url+'/api/state',{headers:{Authorization:'Bearer '+guest.token}})).json();
  assert.ok(!('authoringWorkspace' in guestState.state));assert.ok(!JSON.stringify(guestState).includes('PRIVATE-SHARED-ORIGINAL'));
  await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('#packSavedBlocks summary').click();await page.screenshot({path:'.deps/rule-preparation-workspace-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);console.log('Preparation workspace browser: two preserved reports, one original text, local archive navigation, older installation, saved-block composition, automatic effect, guest isolation and mobile passed. Simulated AI only.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
