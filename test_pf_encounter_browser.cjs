const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  for(const choice of ['parley','combat']){
   const context=await browser.newContext({hasTouch:true}),page=await context.newPage(),actions=[],errors=[];
   page.on('dialog',dialog=>dialog.accept());
   page.on('pageerror',e=>errors.push(e.stack));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push(r.postDataJSON())});
   await page.goto(url);await page.locator('#createForm [name=title]').fill('Patio · '+choice);
   await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Conseguir permiso para pasar');
   await page.locator('#createForm button').click();await page.locator('[data-create-hero]').click();
   await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');
   await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();
   await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
   assert.equal(await page.locator('[data-quick-die="20"]').isVisible(),false);
   const diceActions=actions.length;await page.locator('#quickDiceHelp summary').focus();await page.keyboard.press('Enter');
   assert.equal(await page.locator('[data-quick-die="20"]').isVisible(),true);
   await page.keyboard.press('Enter');assert.equal(actions.length,diceActions);
   await page.locator('#beginPreparedEncounter').click();await page.locator('#pfEncounterEntry').waitFor();
   assert.match(await page.locator('#modalContent').textContent(),/varios caídos.*pendientes/);
   const help=page.locator('#modalContent .encounter-help'),helpActions=actions.length;
   assert.equal(await help.getAttribute('open'),null);
   assert.equal(await help.locator('p').first().isVisible(),false);
   await help.locator('summary').focus();await page.keyboard.press('Enter');
   assert.equal(await help.locator('p').first().isVisible(),true);
   await page.keyboard.press('Enter');assert.equal(actions.length,helpActions);
   const before=actions.length;await page.locator('#pfEncounterEntry button').click();
   await page.locator('#pfEncounterParley').waitFor();assert.equal(actions.length,before+1);
   assert.deepEqual(await page.evaluate(()=>snapshot.state.characters.map(c=>c.hp)),[16,7]);
   assert.equal(await page.evaluate(()=>snapshot.state.characters[1].owner),'director');
   assert.equal(await page.evaluate(()=>snapshot.state.board.active),false);
   const rendered=actions.length;await page.evaluate(()=>refresh(true));assert.equal(actions.length,rendered);
   if(choice==='parley'){
    await page.locator('#pfEncounterParley').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='agreement');
    assert.equal(await page.evaluate(()=>snapshot.state.board.active),false);
    assert.match(await page.locator('#adventureEntry').textContent(),/decisión tuya/);
   }else{
    await page.locator('#grid [data-x="0"][data-y="1"]').click();
    await page.locator('#grid [data-x="0"][data-y="2"]').click();
    await page.locator('#confirmMove').click();await page.waitForFunction(()=>snapshot.state.characters[0].y===2);
    await page.locator('#pfEncounterCombat').click();await page.waitForFunction(()=>snapshot.state.board.active);
    assert.equal(await page.evaluate(()=>snapshot.state.board.autoEnemies),true);
    assert.equal(await page.locator('#startCombat').isVisible(),false);
    assert.equal(await page.locator('#attackButton').isEnabled(),false);
    assert.match(await page.locator('#attackHint').textContent(),/Acércate/);
    await page.locator('#grid [data-x="0"][data-y="1"]').click();await page.locator('#confirmMove').click();
    await page.waitForFunction(()=>!document.querySelector('#attackButton').disabled);
    await page.locator('#attackButton').click();await page.waitForFunction(()=>snapshot.state.characters[1].hp<0);
    const hp=await page.evaluate(()=>snapshot.state.characters[1].hp),con=await page.evaluate(()=>snapshot.state.characters[1].abilities[2]);
    assert.ok(hp>-con);assert.equal(await page.evaluate(()=>snapshot.state.pfEncounter.phase),'combat');
    assert.match(await page.locator('#party [data-character]').nth(1).textContent(),/Moribundo/);
    assert.equal(await page.evaluate(()=>snapshot.state.board.active),true);
    await page.locator('#nextTurn').click();await page.waitForFunction(()=>snapshot.state.characters[1].hp< -5&&!snapshot.state.board.spent[snapshot.state.characters[0].id]?.standard);
    const beforeAid=await page.evaluate(()=>snapshot.state.characters[1].hp);
    await page.locator('#pfFirstAidForm summary').click();await page.locator('#pfFirstAidForm [name=physical]').fill('20');
    await page.setViewportSize({width:390,height:1000});await page.locator('#adventureEntry').scrollIntoViewIfNeeded();
    const mobileHelp=page.locator('#adventureEntry .encounter-help'),beforeHelp=actions.length;
    await mobileHelp.locator('summary').tap();assert.equal(await mobileHelp.locator('p').first().isVisible(),true);
    await mobileHelp.locator('summary').tap();assert.equal(actions.length,beforeHelp);
    assert.match(await page.locator('#pfAidHint').textContent(),/juego calcula/);
    assert.match(await page.locator('#pfEncounterAid').innerText(),/podría morir/);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:'.deps/pf-encounter-entry-mobile.png',fullPage:true});
    await page.locator('#pfFirstAidForm button').click();await page.waitForFunction(()=>snapshot.state.pfEncounter.phase==='resolved');
    assert.equal(await page.evaluate(()=>snapshot.state.board.active),false);
    assert.equal(await page.evaluate(()=>snapshot.state.characters[1].hp),beforeAid);
    assert.equal(await page.evaluate(()=>snapshot.state.characters[1].stable),true);
    assert.match(await page.locator('#party [data-character]').nth(1).textContent(),/Inconsciente y estable/);
    assert.equal(await page.evaluate(()=>snapshot.state.pfEncounter.outcome.status),'stable');
    assert.match(await page.locator('#adventureEntry').textContent(),/inconsciente y estable/);
    await page.reload();await page.waitForFunction(()=>snapshot?.state.pfEncounter.phase==='resolved');
    await page.locator('#adventureEntry').scrollIntoViewIfNeeded();await page.screenshot({path:'.deps/pf-encounter-resolved-mobile.png',fullPage:true});
   }
   assert.ok(!actions.some(a=>['character','create_npc','start_adventure'].includes(a.type)));
   assert.deepEqual(errors,[]);await context.close();
  }
  console.log('PF encounter browser passed: fresh campaign and guided character, catalog NPC, parley/combat, automatic initiative, attack, dying turn, standard-action first aid, stable outcome without HP healing, reload, local consultation and mobile. No AI. Multiple fallen and further continuity remain pending; single-patient recovery is verified in its dedicated browser test.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});

