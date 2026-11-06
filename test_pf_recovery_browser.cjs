const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fatal=process.env.TEST_PF_RECOVERY_CASE==='death';
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],
  {env:{...process.env,TEST_PF_RECOVERY_FIXTURE:fatal?'death':'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext({acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[];
  page.on('dialog',dialog=>dialog.accept());page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');
  await page.locator('#createForm [name=goal]').fill('Disputar el paso por el patio');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();
  await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();
  await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();
  await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!busy);
  assert.equal(await page.evaluate(()=>snapshot.state.pfEncounter.definition.version),'1.1.0');
  // The player explicitly waits each turn. Real NPC attacks cause the fall;
  // no manual HP edits, imported statistics or hourly confirmations.
  for(let n=0;n<6;n++){
   const version=await page.evaluate(()=>snapshot.version);await page.locator('#nextTurn').click();
   await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
  }
  const recovered=await page.evaluate(()=>snapshot.state);
  assert.equal(recovered.characters[0].hp,fatal?-14:-2);assert.equal(recovered.characters[1].hp,7);
  assert.equal(recovered.characters[0].recoveryState?.conscious,fatal?undefined:true);
  assert.equal(recovered.pfEncounter.recoveryOutcome.hours,fatal?12:1);assert.equal(recovered.pfEncounter.recoveryOutcome.seconds,(fatal?12:1)*3600);
  assert.equal(recovered.pfEncounter.recoveryOutcome.status,fatal?'dead':'conscious');assert.equal(recovered.board.active,false);
  assert.equal(await page.locator('#nextTurn').isVisible(),false);
  assert.equal(await page.locator('#requestCheck').isVisible(),!fatal);
  assert.equal(await page.locator('#useAI').isChecked(),false);assert.equal(await page.locator('#useAI').isEnabled(),false);
  assert.match(await page.locator('#adventureEntry').textContent(),fatal?/ha muerto por sus heridas/:/Ahora estás consciente/);
  if(!fatal)assert.match(await page.locator('#adventureEntry').textContent(),/No has recuperado PG/);
  assert.deepEqual(actions.map(a=>a.type),['create_character','enter_pf_encounter','choose_pf_encounter',...Array(6).fill('turn')]);
  const audit=page.locator('.recovery-audit'),beforeAudit=actions.length;
  assert.equal(await audit.count(),1);assert.equal(await audit.locator('p').count(),fatal?12:1);assert.equal(await audit.locator('p').first().isVisible(),false);
  await audit.locator('summary').focus();await page.keyboard.press('Enter');
  assert.match(await audit.textContent(),fatal?/d20 1,/:/d20 18/);assert.equal(await audit.locator('p').first().isVisible(),true);
  await page.keyboard.press('Enter');assert.equal(actions.length,beforeAudit);
  await page.locator('#party [data-character]').first().click();await page.locator('.sheet-checks').waitFor();
  assert.match(await page.locator('.sheet-checks .notice').textContent(),fatal?/ha muerto/:/incapacitado/);
  await page.locator('#closeModal').click();await page.locator('[data-tab=journal]').click();
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);
  const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());
  await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
  assert.deepEqual(await page.evaluate(()=>snapshot.state.pfEncounter),recovered.pfEncounter);
  await page.reload();await page.waitForFunction(status=>snapshot?.state.pfEncounter.recoveryOutcome?.status===status,fatal?'dead':'conscious');
  await page.setViewportSize({width:390,height:1000});await page.locator('[data-tab=story]').click();
  await page.locator('#adventureEntry').scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:fatal?'.deps/pf-recovery-death-mobile.png':'.deps/pf-recovery-automatic-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('PF recovery browser passed: guided character, genuine NPC attacks, automatic stabilization and hourly consciousness without healing or per-hour administration, clear disabled-state notice, UI export/import, reload and mobile. No AI. Multiple fallen and later continuity remain pending.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
