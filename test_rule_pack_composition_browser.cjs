const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_RULE_PACK_FIXTURE:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext(),room=await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Reglas por bloques',ruleset:'rule-pack'}})).json();
  const base=JSON.parse(fs.readFileSync('test_fixtures/rule_packs/original-pool-example.json','utf8'));
  const headers={Authorization:'Bearer '+room.token},state=await (await context.request.get(url+'/api/state',{headers})).json();
  assert.ok((await context.request.post(url+'/api/action',{headers,data:{id:'base-install',version:state.version,type:'install_rule_pack',package:base}})).ok());
  await context.addInitScript(t=>{if(!localStorage.getItem('cronicas-token'))localStorage.setItem('cronicas-token',t)},room.token);
  const extra=structuredClone(base);extra.version='1.0.1';
  extra.sources.push({id:'reserve-example',title:'Original reserve example',edition:'1',locator:'Initial reserve 2; using one requires a positive reserve.'});
  extra.fields.reserve={type:'integer',label:'Reserva',initial:2,min:0,max:2,sources:['reserve-example']};
  extra.actions.use_reserve={label:'Usar reserva',sources:['reserve-example'],inputs:{},requires:[{op:'gt',args:[{ref:['fields','reserve']},0]}],rolls:[],effects:[{field:'reserve',value:{op:'sub',args:[{ref:['fields','reserve']},1]}}]};
  const page=await context.newPage(),actions=[],previews=[],errors=[];
  page.on('pageerror',e=>errors.push(e.stack));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON());if(r.url().endsWith('/api/rule-pack/compose'))previews.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#packComposeFiles').waitFor();
  const wrong=structuredClone(extra);wrong.fields.energy.initial=2;
  await page.locator('#packComposeFiles').setInputFiles({name:'conflict.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(wrong))});
  await page.locator('#packComposePreview button').click();
  await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('incompatibles'));
  assert.equal(actions.length,0);assert.equal(await page.evaluate(()=>snapshot.state.package.document.version),'1.0.0');await page.locator('#closeModal').click();
  await page.locator('#packComposeFiles').setInputFiles({name:'reserve.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(extra))});
  await page.locator('#packComposePreview [name=versionTarget]').fill('1.1.0');assert.equal(actions.length,0);assert.equal(previews.length,1);
  await page.locator('#packComposePreview button').click();await page.locator('#packComposeInstall').waitFor();assert.equal(actions.length,0);
  let lost=false;await page.route('**/api/action',async route=>{
   if(!lost&&route.request().postDataJSON()?.type==='compose_rule_pack'){lost=true;await route.fetch();await route.abort('connectionfailed')}
   else await route.continue();
  });
  await page.locator('#packComposeInstall button').click();
  await page.waitForFunction(()=>snapshot.state.package.document.version==='1.1.0'&&localStorage.getItem('cronicas-pending'));
  const pending=await page.evaluate(()=>JSON.parse(localStorage.getItem('cronicas-pending')));
  await page.reload();await page.locator('#packActivate').waitFor();
  assert.equal(actions.at(-1).id,pending.body.id);assert.equal(await page.evaluate(()=>localStorage.getItem('cronicas-pending')),null);
  assert.equal(await page.evaluate(()=>snapshot.state.package.composition.inputs.length),2);
  await page.unroute('**/api/action');await page.locator('#packActivate').click();await page.locator('#packInstall [name=use]').check();await page.locator('#packInstall button').click();
  await page.locator('#packCreate [name=name]').fill('Lúa');await page.locator('#packCreate button').click();
  await page.locator('[data-pack-action=use_reserve]').click();await page.locator('#packAction button').click();await page.locator('#modal').waitFor({state:'hidden'});
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.reserve),1);
  assert.equal(await page.evaluate(()=>snapshot.state.package.composition.inputs.length),2);assert.equal(await page.locator('#packComposeFiles').count(),0);
  await page.locator('[data-pack-action=attempt]').click();await page.locator('#packAction button').click();await page.locator('#modal').waitFor({state:'hidden'});
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].sheet.fields.energy),2);
  await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:'.deps/rule-pack-composition-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);console.log('Composition browser: conflict rejection, explicit preview, no preview writes, lost-response recovery, draft activation preserving provenance, both block actions and mobile passed. No AI.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
