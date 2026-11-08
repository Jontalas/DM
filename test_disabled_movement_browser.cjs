const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{env:{...process.env,TEST_PF_ENCOUNTER_VERSION:'1.11.0',TEST_PF_CEASEFIRE_FIXTURE:'1',TEST_PF_TRUCE_NIGHT:'1'},stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{createInterface({input:fixture.stdout}).once('line',resolve);fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const page=await browser.newPage({hasTouch:true}),actions=[],errors=[];page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Revisar movimiento al quedar incapacitada');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry button').click();await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active&&!busy);await page.locator('#attackButton').click();await page.waitForFunction(()=>snapshot.state.characters[1].hp===1&&!busy);
  for(let turn=0;turn<4;turn++){await page.locator('#nextTurn').click();await page.waitForFunction(hp=>snapshot.state.characters[0].hp===hp&&!busy,12-turn*4)}
  assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hp),0);const before=await page.evaluate(()=>structuredClone(snapshot.state)),count=actions.length;
  assert.match(await page.locator('#actionBudget').textContent(),/Incapacitado.*3 casillas/);
  assert.match(await page.locator('#attackButton').textContent(),/perderás 1 PG/);assert.match(await page.locator('#attackHint').textContent(),/volverás a quedar moribundo/);assert.equal(await page.locator('#attackButton').getAttribute('aria-describedby'),'attackHint');
  for(let y=1;y<=4;y++)await page.locator(`#grid [data-x="0"][data-y="${y}"]`).click();
  assert.equal(await page.locator('#confirmMove').isEnabled(),false);assert.match(await page.locator('#pathInfo').textContent(),/supera las 3 casillas/);
  await page.locator('#clearPath').click();for(let y=1;y<=3;y++)await page.locator(`#grid [data-x="0"][data-y="${y}"]`).click();assert.equal(await page.locator('#confirmMove').isEnabled(),true);
  // Presentation-only probes. No move is confirmed: opportunity attacks still
  // require explicit adjudication; HTTP tests separately commit a legal move.
  await page.evaluate(()=>{snapshot.state.board.spent[snapshot.state.characters[0].id]={move:true};renderBoard()});
  assert.equal(await page.locator('#confirmMove').isEnabled(),false);assert.match(await page.locator('#boardGuidance').textContent(),/Ya has usado tus acciones/);
  await page.evaluate(()=>{const c=snapshot.state.characters[0];c.hp=-c.abilities[2]+1;c.stable=true;c.recoveryState={conscious:true};snapshot.state.board.spent[c.id]={};renderBoard();renderAttack()});
  assert.match(await page.locator('#attackHint').textContent(),/morirás por tus heridas/);
  await page.evaluate(()=>{snapshot.state.characters[0].hp=-1;snapshot.state.characters[0].stable=true;delete snapshot.state.characters[0].recoveryState;renderBoard()});
  assert.equal(await page.locator('#confirmMove').isEnabled(),false);assert.match(await page.locator('#pathInfo').textContent(),/No puede moverse/);
  await page.evaluate(()=>refresh(true));assert.deepEqual(await page.evaluate(()=>snapshot.state.characters),before.characters);assert.equal(actions.length,count);
  await page.setViewportSize({width:390,height:1000});await page.locator('[data-tab=board]').tap();await page.locator('#board').scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.equal(actions.length,count);await page.screenshot({path:'.deps/disabled-movement-mobile.png',fullPage:true});assert.deepEqual(errors,[]);
  console.log('Disabled movement UI verified: organic fall to0, four-cell preview blocked/three allowed, spent-action and unconscious presentation probes, state unchanged with zero movement POST, mobile/touch. Dice simulated; no opportunity attacks assumed.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
