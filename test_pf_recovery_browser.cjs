const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fatal=process.env.TEST_PF_RECOVERY_CASE==='death';
 const armored=process.env.TEST_PF_RECOVERY_CASE==='armor';
 const corrected=process.env.TEST_PF_RECOVERY_CASE==='correction';
 const shared=process.env.TEST_PF_RECOVERY_CASE==='shared';
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],
  {env:{...process.env,TEST_PF_ENCOUNTER_VERSION:'1.4.0',TEST_PF_RECOVERY_FIXTURE:shared?'shared':fatal?'death':'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext({acceptDownloads:true}),page=await context.newPage(),actions=[],errors=[];
  page.on('dialog',dialog=>dialog.accept());page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');
  await page.locator('#createForm [name=goal]').fill('Disputar el paso por el patio');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();
  await page.locator('#creatorName').fill('Aria');
  await page.locator('[data-creator-step="3"]').click();
  if(armored)await page.locator('[data-creator-field=armor]').selectOption('scale');
  await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  await page.locator('#beginPreparedEncounter').click();
  if(armored)assert.match(await page.locator('#modalContent .recovery-limit').textContent(),/cota de escamas/);
  await page.locator('#pfEncounterEntry button').click();
  await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!busy);
  assert.equal(await page.evaluate(()=>snapshot.state.pfEncounter.definition.version),'1.4.0');
  // The player explicitly waits each turn. Real NPC attacks cause the fall;
  // no manual HP edits, imported statistics or hourly confirmations.
  for(let n=0;n<(shared?4:6);n++){
   const version=await page.evaluate(()=>snapshot.version);await page.locator('#nextTurn').click();
   await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
  }
  if(shared){
   assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hp),0);
   assert.match(await page.locator('#party [data-character]').first().textContent(),/Incapacitado/);
   await page.locator('#attackButton').click();
   await page.waitForFunction(()=>snapshot.state.pfEncounter.recoveryOutcome&&!busy);
  }
  const recovered=await page.evaluate(()=>snapshot.state);
  if(armored){
   assert.equal(recovered.characters[0].hp,-2);assert.equal(recovered.characters[0].stable,true);
   assert.equal(recovered.pfEncounter.recoveryLimit,'armor-rest');assert.equal(recovered.pfEncounter.recoveryOutcome,undefined);
   assert.equal(recovered.worldTime,'Comienzo de la aventura');assert.equal(recovered.board.active,false);
   assert.match(await page.locator('#adventureEntry').textContent(),/No se han avanzado horas/);
   assert.match(await page.locator('#party [data-character]').first().textContent(),/Inconsciente y estable/);
   await page.locator('[data-tab=journal]').click();
   const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);
   const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());
   await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.pfEncounter),recovered.pfEncounter);
   await page.reload();await page.waitForFunction(()=>snapshot?.state.pfEncounter.recoveryLimit==='armor-rest');
   await page.setViewportSize({width:390,height:1000});await page.locator('[data-tab=story]').click();
   await page.locator('#adventureEntry').scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:'.deps/pf-recovery-armor-mobile.png',fullPage:true});assert.deepEqual(errors,[]);
   console.log('PF recovery armor browser passed: legal scale armor, advance warning, real NPC attacks, stable fall without skipped fatigue or hourly advancement, preserved copy/reload and mobile. No AI.');
   return;
  }
  assert.equal(recovered.characters[0].hp,shared?-1:fatal?-14:-2);assert.equal(recovered.characters[1].hp,shared?-5:7);
  if(shared)assert.equal(recovered.characters[1].recoveryState.conscious,true);
  assert.equal(recovered.characters[0].recoveryState?.conscious,fatal?undefined:true);
  assert.equal(recovered.pfEncounter.recoveryOutcome.hours,fatal?12:1);assert.equal(recovered.pfEncounter.recoveryOutcome.seconds,(fatal?12:1)*3600);
  assert.equal(recovered.pfEncounter.recoveryOutcome.status,fatal?'dead':'conscious');assert.equal(recovered.board.active,false);
  assert.match(await page.locator('#party [data-character]').first().textContent(),fatal?/Ha muerto/:/Incapacitado/);
  assert.equal(await page.locator('#nextTurn').isVisible(),false);
  const manualWasOpen=await page.locator('#board .board-help').evaluate(e=>e.open);if(!manualWasOpen)await page.locator('#board .board-help > summary').click();
  assert.equal(await page.locator('#requestCheck').isVisible(),!fatal);
  if(!manualWasOpen)await page.locator('#board .board-help > summary').click();
  assert.equal(await page.locator('#useAI').isChecked(),false);assert.equal(await page.locator('#useAI').isEnabled(),false);
  assert.match(await page.locator('#adventureEntry').textContent(),fatal?/ha muerto por sus heridas/:/Ahora estás consciente/);
  if(!fatal)assert.match(await page.locator('#adventureEntry').textContent(),/No has recuperado PG/);
  assert.deepEqual(actions.map(a=>a.type),['create_character','enter_pf_encounter','choose_pf_encounter',...Array(shared?4:6).fill('turn'),...(shared?['attack']:[])]);
  const audit=page.locator('.recovery-audit'),beforeAudit=actions.length;
  assert.equal(await audit.count(),1);assert.equal(await audit.locator('p').count(),shared?2:fatal?12:1);assert.equal(await audit.locator('p').first().isVisible(),false);
  await audit.locator('summary').focus();await page.keyboard.press('Enter');
  assert.match(await audit.textContent(),fatal?/d20 1,/:/d20 18/);assert.equal(await audit.locator('p').first().isVisible(),true);
  await page.keyboard.press('Enter');assert.equal(actions.length,beforeAudit);
  await page.locator('#party [data-character]').first().click();await page.locator('.sheet-checks').waitFor();
  assert.match(await page.locator('.sheet-checks .notice').textContent(),fatal?/ha muerto/:/incapacitado/);
  assert.equal(await page.locator('.sheet-free-roll').getAttribute('open'),null);
  if(fatal)assert.equal(await page.locator('[data-sheet-check]').isEnabled(),false);
  await page.locator('#closeModal').click();
  if(corrected){
   await page.locator('#board .board-help > summary').click();await page.locator('#manualBtn').click();
   await page.locator('#manualForm [name=reason]').fill('Corrección excepcional del fixture');
   await page.locator('#manualForm [name=reference]').fill('Prueba de preservación del estado');
   await page.locator('#manualForm [name=resolution]').fill('Se corrige1PG sin repetir la recuperación');
   await page.locator('#manualForm [name=character]').selectOption(recovered.characters[0].id);
   await page.locator('#manualForm [name=hpDelta]').fill('1');
   let version=await page.evaluate(()=>snapshot.version);await page.locator('#manualForm button').click();
   await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
   assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hp),-1);
   assert.equal(await page.evaluate(()=>snapshot.state.characters[0].recoveryState.conscious),true);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.characters[0].recoveryState.lastCheck),recovered.characters[0].recoveryState.lastCheck);
   await page.locator('#party [data-character]').first().click();await page.locator('#characterAdvanced > summary').click();await page.locator('#advancedCharacterEdit').click();
   await page.locator('#characterForm [name=notes]').fill('Una nota posterior sin cambiar la salud');
   version=await page.evaluate(()=>snapshot.version);await page.locator('#characterForm button.primary').click();
   await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
   assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hp),-1);
   assert.equal(await page.evaluate(()=>snapshot.state.characters[0].recoveryState.conscious),true);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.characters[0].recoveryState.lastCheck),recovered.characters[0].recoveryState.lastCheck);
  }
  await page.locator('[data-tab=journal]').click();
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#exportBtn').click()]);
  const version=await page.evaluate(()=>snapshot.version);await page.locator('#importFile').setInputFiles(await download.path());
  await page.waitForFunction(v=>snapshot.version>v&&!busy,version);
  assert.deepEqual(await page.evaluate(()=>snapshot.state.pfEncounter),recovered.pfEncounter);
  await page.reload();await page.waitForFunction(status=>snapshot?.state.pfEncounter.recoveryOutcome?.status===status,fatal?'dead':'conscious');
  await page.setViewportSize({width:390,height:1000});await page.locator('[data-tab=story]').click();
  await page.locator('#adventureEntry').scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:shared?'.deps/pf-recovery-shared-mobile.png':corrected?'.deps/pf-recovery-correction-mobile.png':fatal?'.deps/pf-recovery-death-mobile.png':'.deps/pf-recovery-automatic-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);
  console.log(shared?'PF shared recovery browser passed: both fall through real attacks and disabled action cost, recover on their own initiative counts without healing, preserve copy/reload/mobile. No AI. Full rest and later continuity remain pending.':corrected?'PF health correction browser passed: explicit HP correction and advanced note edit preserve consciousness and the original check; UI copy/reload/mobile remain valid. No AI.':'PF recovery browser passed: guided character, genuine NPC attacks, automatic stabilization and hourly consciousness without healing or per-hour administration, clear disabled-state notice, UI export/import, reload and mobile. No AI. Full rest and later continuity remain pending.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
