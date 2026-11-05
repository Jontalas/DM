const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_RULE_PACK_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Archivo privado separado',ruleset:'rule-pack'}})).json();
  await context.addInitScript(t=>{if(!localStorage.getItem('cronicas-token'))localStorage.setItem('cronicas-token',t)},room.token);
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.stack));
  await page.goto(url);await page.locator('#packPrepareOpen').click();
  for(const [name,value] of Object.entries({title:'Reglas privadas del ejemplo',edition:'Original 1',scope:'Recurso y dados',attribution:'Ejemplo propio',text:'Initial energy 3; attempts require positive energy, spend 1, roll 2d6 and succeed on 7 to 12. Energy 0 triggers exhaustion. PRIVATE-ASSET-ORIGINAL'}))await page.locator(`#packPrepare [name=${name}]`).fill(value);
  await page.locator('#packPrepare button[type=submit]').click();await page.locator('#modal').waitFor({state:'hidden'});
  const reference=await page.evaluate(()=>snapshot.state.authoringWorkspaceRef.sha256);
  assert.equal(await page.evaluate(()=>Object.keys(snapshot.state.authoringWorkspace.blocks).length),1);
  const refreshed=page.waitForResponse(r=>r.url().includes('/api/state?')&&r.request().url().includes('workspace='));
  await page.evaluate(()=>refresh(true));const payload=await (await refreshed).json();
  assert.equal(payload.workspaceUnchanged,reference);assert.equal(payload.state.authoringWorkspace,null);
  assert.ok(!JSON.stringify(payload).includes('PRIVATE-ASSET-ORIGINAL'));
  await page.locator('#packPreparationReport').click();await page.locator('#packReviewPrepared').click();await page.locator('#packInstall [name=use]').check();await page.locator('#packInstall button').click();
  await page.locator('#packCreate [name=name]').fill('Lúa');await page.locator('#packCreate button').click();
  await page.locator('[data-pack-action]').click();
  const gameResponse=page.waitForResponse(r=>r.url().includes('/api/state?')&&r.request().url().includes('workspace='));
  await page.locator('#packAction button').click();await page.locator('#modal').waitFor({state:'hidden'});
  const update=await (await gameResponse).json();assert.equal(update.workspaceUnchanged,reference);assert.equal(update.state.authoringWorkspace,null);
  assert.equal(await page.evaluate(()=>Object.keys(snapshot.state.authoringWorkspace.blocks).length),1);
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.energy),2);
  const exportData=await (await context.request.post(url+'/api/export',{headers:{Authorization:'Bearer '+room.token},data:{}})).json();
  assert.equal(exportData.state.authoringWorkspaceRef,null);assert.ok(JSON.stringify(exportData.state.authoringWorkspace).includes('PRIVATE-ASSET-ORIGINAL'));
  const firstLoad=page.waitForResponse(r=>r.url().endsWith('/api/state'));
  await page.reload();await page.locator('#packPreparationReport').waitFor();
  assert.ok((await (await firstLoad).json()).state.authoringWorkspace);
  // A slow response from the old access must not replace a newly opened campaign.
  let release,started;const gate=new Promise(resolve=>release=resolve),caught=new Promise(resolve=>started=resolve);let intercept=true;
  await page.route('**/api/state*',async route=>{
   if(intercept&&route.request().headers().authorization==='Bearer '+room.token){intercept=false;const response=await route.fetch();started();await gate;await route.fulfill({response});}
   else await route.continue();
  });
  await page.evaluate(()=>{window.oldPrivateRefresh=refresh(true)});await caught;
  const other=await (await context.request.post(url+'/api/create',{data:{player:'Eva',title:'Otra campaña',ruleset:'rule-pack'}})).json();
  await page.evaluate(async t=>{token=t;localStorage.setItem('cronicas-token',t);await refresh(true)},other.token);
  const newId=await page.evaluate(()=>snapshot.id);release();await page.evaluate(()=>window.oldPrivateRefresh);
  assert.equal(await page.evaluate(()=>snapshot.id),newId);assert.equal(await page.evaluate(()=>snapshot.title),'Otra campaña');
  assert.equal(await page.evaluate(()=>snapshot.state.authoringWorkspace),null);
  await page.unroute('**/api/state*');assert.deepEqual(errors,[]);
  console.log('Private assets browser: first load, unchanged-payload omission, local report cache, game updates without source transfer, complete export, reload and access-switch race passed. Simulated AI only.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
