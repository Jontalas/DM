const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process');
const {createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const host=await browser.newContext(),guest=await browser.newContext();
  const token=(await (await host.request.post(url+'/api/create',{data:{player:'Ana',title:'Checks'}})).json()).token;
  const headers={Authorization:'Bearer '+token};
  const room=await (await host.request.get(url+'/api/state',{headers})).json();
  const player=(await (await guest.request.post(url+'/api/join',{data:{name:'Luis',invite:room.invite}})).json()).token;
  const gh={Authorization:'Bearer '+player};let roomVersion=(await (await guest.request.get(url+'/api/state',{headers:gh})).json()).version;
  const added=await guest.request.post(url+'/api/action',{headers:gh,data:{id:'new-character',version:roomVersion,type:'character',character:{name:'Aria',abilities:[9,16,12,10,14,8],saves:[4,6,2],skillTotals:[{name:'Percepción',total:8}]}}});assert.ok(added.ok());
  await host.addInitScript(t=>localStorage.setItem('cronicas-token',t),token);await guest.addInitScript(t=>localStorage.setItem('cronicas-token',t),player);
  const a=await host.newPage(),b=await guest.newPage(),errors=[];
  for(const page of [a,b]){page.on('pageerror',e=>errors.push(e.message));await page.goto(url);await page.locator('#app').waitFor({state:'visible'})}
  assert.equal(await b.locator('#requestCheck').isVisible(),false);
  // Director preparation is available to the host, never displayed to a guest.
  for(const page of [a,b])await page.locator('[data-tab="journal"]').click();
  assert.equal(await a.locator('[name=directorNotes]').isVisible(),false);
  await a.locator('#journalEdit > summary').click();
  assert.equal(await a.locator('[name=directorNotes]').isVisible(),true);
  assert.equal(await b.locator('[name=directorNotes]').isVisible(),false);
  for(const page of [a,b])await page.locator('nav [data-tab="story"]').click();
  await a.locator('[data-tab=dice]').click();assert.equal(await a.locator('[data-dice-character]').count(),0);assert.equal(await a.locator('#diceCharacters [data-dice-create]').isVisible(),true);
  const beforeDiceEntry=await b.evaluate(()=>snapshot.version);await b.locator('[data-tab=dice]').click();assert.equal(await b.locator('[data-dice-character]').count(),1);assert.equal(await b.locator('#rollForm').isVisible(),false);await b.locator('#manualDiceTools>summary').focus();await b.keyboard.press('Enter');assert.equal(await b.locator('#rollForm').isVisible(),true);await b.keyboard.press('Enter');await b.locator('[data-dice-character]').focus();await b.keyboard.press('Enter');assert.equal(await b.evaluate(()=>snapshot.version),beforeDiceEntry);
  assert.equal(await b.locator('#characterForm').count(),0);assert.equal(await b.locator('[data-sheet-check]').isVisible(),true);assert.equal(await b.locator('[data-sheet-selection]').evaluate(e=>e===document.activeElement),true);
  await b.keyboard.press('Escape');assert.equal(await b.locator('#dice').isVisible(),true);assert.equal(await b.locator('[data-dice-character]').evaluate(e=>e===document.activeElement),true);await b.keyboard.press('Enter');
  if(process.env.TEST_CHECK_SELECTION_IDENTITY==='1'){
   const current=await b.evaluate(()=>snapshot),original=current.state.characters[0];
   const save=async(skills,id)=>{const version=(await(await guest.request.get(url+'/api/state',{headers:gh})).json()).version;const response=await guest.request.post(url+'/api/action',{headers:gh,data:{id,version,type:'character',character:{...original,skillTotals:skills}}});assert.ok(response.ok());await b.evaluate(()=>refresh())};
   await save([{name:'Sigilo',total:5},{name:'Percepci\u00f3n',total:8}],'reorder-skills');
   await b.locator('[data-sheet-selection]').selectOption('0');await b.locator('[data-sheet-selection]').selectOption('9');
   assert.equal(await b.locator('[data-sheet-check]').getAttribute('data-check-key'),'Percepci\u00f3n','An open option must keep its skill identity after reordering');
   await save(original.skillTotals,'restore-skills');
   await a.evaluate(()=>{requestCheckForm()});
   await a.locator('#requestCheckForm [name=selection]').selectOption('9');
   await a.locator('#requestCheckForm [name=reason]').fill('Verify stable skill identity');
   await save([{name:'Sigilo',total:5},{name:'Percepci\u00f3n',total:8}],'reorder-request-skills');await a.evaluate(()=>refresh());
   await a.locator('#requestCheckForm button.primary').click();await a.locator('#modal').waitFor({state:'hidden'});
   const requested=await a.evaluate(()=>snapshot);assert.equal(requested.state.pending.find(p=>p.check).check.key,'Percepci\u00f3n');
   const cancelled=await host.request.post(url+'/api/action',{headers,data:{id:'cancel-identity-request',version:requested.version,type:'cancel_check',request:requested.state.pending.find(p=>p.check).check.id}});assert.ok(cancelled.ok());
   await save(original.skillTotals,'restore-request-skills');await a.evaluate(()=>refresh());

  }
  const countBeforeChoice=await b.evaluate(()=>snapshot.version);
  await b.locator('[data-sheet-selection]').selectOption('0');
  assert.equal(await b.locator('[data-check-key="str"]').textContent(),'Tirar Fuerza (-1)');
  await b.locator('[data-sheet-selection]').selectOption('9');
  assert.equal(await b.evaluate(()=>snapshot.version),countBeforeChoice);
  let interruptCheck=true,offline=false,checkPosts=0;b.on('request',r=>{if(r.url().endsWith('/api/action')&&r.postDataJSON().type==='check')checkPosts++});
  await b.route('**/api/state**',route=>offline?route.abort('connectionfailed'):route.continue());await b.route('**/api/action',async route=>{if(interruptCheck&&route.request().postDataJSON().type==='check'){interruptCheck=false;const response=await route.fetch();offline=true;await route.fulfill({response})}else await route.continue()});
  await b.locator('[data-check-key="Percepción"]').click();
  await b.waitForFunction(()=>!busy&&JSON.parse(localStorage.getItem('cronicas-pending')||'null')?.confirmed===true);assert.equal(await b.locator('#playGuidance').isVisible(),true);offline=false;await b.locator('#playGuidanceAction').click();await b.waitForFunction(()=>!busy&&!localStorage.getItem('cronicas-pending'));assert.equal(checkPosts,1);
  await b.waitForFunction(()=>snapshot.state.messages.at(-1).check?.total===20);
  await b.locator('#modal').waitFor({state:'hidden'});assert.equal(await b.locator('#story').isVisible(),true);
  assert.match(await b.locator('#messages .check-result').textContent(),/Tirada libre.*Percepción/);
  const audit=b.locator('#messages .check-audit').first(),beforeAudit=await b.evaluate(()=>snapshot.version);
  assert.equal(await audit.locator('p').isVisible(),false);
  await audit.locator('summary').focus();await b.keyboard.press('Enter');
  assert.match(await audit.locator('p').textContent(),/d20 12.*\+8 = 20/);
  if(process.env.TEST_MESSAGE_HISTORY==='1'){
   await b.setViewportSize({width:390,height:600});await audit.locator('summary').focus();await b.locator('#story').evaluate(e=>{e.scrollTop=e.scrollHeight});const beforeScroll=await b.locator('#story').evaluate(e=>e.scrollTop);await b.evaluate(()=>{window.keptAudit=document.querySelector('#messages .check-audit');window.keptAuditSummary=window.keptAudit.querySelector('summary')});
   const current=await (await host.request.get(url+'/api/state',{headers})).json();const response=await host.request.post(url+'/api/action',{headers,data:{id:'incoming-while-audit',version:current.version,type:'talk',kind:'ooc',text:'Nota del grupo mientras revisas la tirada.',director:false,captureContract:'pf-director-action-1'}});assert.equal(response.ok(),true);await b.evaluate(()=>refresh(true));
   assert.equal(await audit.evaluate(e=>e.open),true,'An incoming message must not close the calculation being read');assert.equal(await b.evaluate(()=>document.querySelector('#messages .check-audit')===window.keptAudit),true);assert.equal(await b.evaluate(()=>document.activeElement===window.keptAuditSummary),true);assert.ok(Math.abs(await b.locator('#story').evaluate(e=>e.scrollTop)-beforeScroll)<=1,'Reading an old calculation must not follow the newest message');assert.match(await b.locator('#messages .message').last().textContent(),/Nota del grupo/);assert.equal(checkPosts,1);
   // Rendering the same public history is inert, including key-order differences.
   const inert=await b.evaluate(async()=>{let mutations=0;const observer=new MutationObserver(records=>mutations+=records.length);observer.observe(document.querySelector('#messages'),{childList:true,characterData:true,subtree:true});const index=snapshot.state.messages.findIndex(m=>m.check);snapshot.state.messages[index]=Object.fromEntries(Object.entries(snapshot.state.messages[index]).reverse());render();await Promise.resolve();observer.disconnect();return mutations});assert.equal(inert,0);assert.equal(await audit.evaluate(e=>e.open),true);
   const incoming=async(kind,text,id)=>{const row=await (await host.request.get(url+'/api/state',{headers})).json();assert.equal((await host.request.post(url+'/api/action',{headers,data:{id,version:row.version,type:'talk',kind,text,director:false,captureContract:'pf-director-action-1'}})).ok(),true)};
   // Text selection stays attached to the old audit while another public note arrives.
   await b.locator('#message').focus();const selectedText=await b.evaluate(()=>{const range=document.createRange();range.selectNodeContents(document.querySelector('#messages .check-audit p'));const selected=getSelection();selected.removeAllRanges();selected.addRange(range);return selected.toString()});assert.ok(selectedText.length>0);const selectedScroll=await b.locator('#story').evaluate(e=>e.scrollTop);await incoming('ooc','Segunda nota pública de la prueba.','incoming-while-selection');await b.evaluate(()=>refresh(true));assert.equal(await b.evaluate(()=>getSelection().toString()),selectedText);assert.equal(await b.locator('#message').evaluate(e=>e===document.activeElement),true);assert.ok(Math.abs(await b.locator('#story').evaluate(e=>e.scrollTop)-selectedScroll)<=1);await b.evaluate(()=>getSelection().removeAllRanges());
   // Current display names can change without closing the unchanged historical evidence.
   await audit.locator('summary').focus();await b.evaluate(()=>{window.historyOriginalName=snapshot.state.characters[0].name;snapshot.state.characters[0].name='Aria renombrada';render()});assert.match(await b.locator('#messages .check-result').first().textContent(),/Aria renombrada/);assert.equal(await audit.evaluate(e=>e.open),true);assert.equal(await audit.locator('summary').evaluate(e=>e===document.activeElement),true);await b.evaluate(()=>{snapshot.state.characters[0].name=window.historyOriginalName;delete window.historyOriginalName;render()});
   // Identical imported records still have separate rows; removing the probe preserves the first.
   const originalRows=await b.locator('#messages > .message').count();await b.evaluate(()=>{snapshot.state.messages.push(structuredClone(snapshot.state.messages.find(m=>m.check)));render()});assert.equal(await b.locator('#messages > .message').count(),originalRows+1);assert.equal(await b.locator('#messages .check-audit').count(),2);assert.equal(await b.locator('#messages .check-audit').last().evaluate(e=>e.open),false);await b.evaluate(()=>{snapshot.state.messages.pop();render()});assert.equal(await audit.evaluate(e=>e.open),true);
   // A host-private write changes the version, not the guest's visible history.
   await incoming('private','Nota privada de Ana para la prueba de historial.','private-while-audit');const privateUpdate=await b.evaluate(async()=>{let changes=0;const observer=new MutationObserver(records=>changes+=records.length);observer.observe(document.querySelector('#messages'),{childList:true,characterData:true,subtree:true});await refresh(true);await Promise.resolve();observer.disconnect();return changes});assert.equal(privateUpdate,0);assert.doesNotMatch(await b.locator('#messages').textContent(),/Nota privada de Ana/);assert.equal(await audit.evaluate(e=>e.open),true);assert.equal(await audit.locator('summary').evaluate(e=>e===document.activeElement),true);
   const guestIdentity=await b.evaluate(()=>snapshot.id+':'+snapshot.me.id),hostState=await (await host.request.get(url+'/api/state',{headers})).json(),hostIdentity=hostState.id+':'+hostState.me.id;await b.evaluate(({row,access})=>CampaignLibrary.record(localStorage,row,access),{row:hostState,access:token});await b.evaluate(()=>{window.guestHistoryRow=document.querySelector('#messages > .message');window.guestJournalHeading=document.querySelector('#journalOverview h3')});
   await b.locator('#libraryBtn').click();await b.locator('#modal [data-library-open="'+hostIdentity+'"]:not([data-library-character])').click();await b.waitForFunction(id=>snapshot.me.id===id&&!busy,hostState.me.id);assert.match(await b.locator('#messages .private').textContent(),/Nota privada de Ana/);assert.equal(await b.evaluate(()=>window.guestHistoryRow.isConnected),false);assert.equal(await b.evaluate(()=>window.guestJournalHeading.isConnected),false);assert.equal(await audit.evaluate(e=>e.open),false);await b.evaluate(()=>{window.hostPrivateRow=document.querySelector('#messages .private')});
   await b.locator('#libraryBtn').click();await b.locator('#modal [data-library-open="'+guestIdentity+'"]:not([data-library-character])').click();await b.waitForFunction(id=>snapshot.me.id!==id&&!busy,hostState.me.id);assert.equal(await b.locator('#messages .private').count(),0);assert.equal(await b.evaluate(()=>window.hostPrivateRow.isConnected),false);assert.equal(await audit.evaluate(e=>e.open),false);assert.equal(checkPosts,1);await audit.locator('summary').focus();await b.keyboard.press('Enter');
   await b.setViewportSize({width:1280,height:900});
  }
  await b.keyboard.press('Enter');assert.equal(await b.evaluate(()=>snapshot.version),beforeAudit+(process.env.TEST_MESSAGE_HISTORY==='1'?3:0));
  await a.reload();await a.locator('#app').waitFor({state:'visible'});
  if(await a.locator('[data-tab=board]').isVisible())await a.locator('[data-tab=board]').click();await a.locator('#board .board-help > summary').click();
  await a.locator('#requestCheck').click();
  await a.locator('#requestCheckForm [name=selection]').selectOption('6');
  await a.locator('#requestCheckForm [name=dc]').fill('16');
  await a.locator('#requestCheckForm [name=reason]').fill('Resistir el peligro');
  await a.locator('#requestCheckForm button').click();await a.locator('.check-request').waitFor();
  await b.reload();await b.locator('.check-request').waitFor();
  assert.match(await b.locator('#playGuidanceText').textContent(),/tirada pendiente/);
  const beforeGuide=await b.evaluate(()=>snapshot.version);
  await b.locator('#playGuidanceAction').click();
  assert.equal(await b.locator('[data-resolve-check]').evaluate(el=>el===document.activeElement),true);
  assert.equal(await b.evaluate(()=>snapshot.version),beforeGuide);
  await b.setViewportSize({width:390,height:1000});
  await b.locator('#playGuidance').scrollIntoViewIfNeeded();
  assert.ok(await b.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await b.screenshot({path:'.deps/play-guidance-pending-mobile.png',fullPage:true});
  await b.setViewportSize({width:1280,height:900});
  // Local rendering probe; no injury is written to the campaign.
  await b.evaluate(()=>{window.savedCheckActor=structuredClone(snapshot.state.characters[0]);snapshot.state.characters[0].hp=-1;snapshot.state.characters[0].stable=false;renderChecks();renderPlayGuidance(snapshot.state)});
  assert.equal(await b.locator('[data-resolve-check]').isEnabled(),false);
  assert.match(await b.locator('#playGuidanceText').textContent(),/revisar el estado/);
  await b.evaluate(()=>{snapshot.state.characters[0]=window.savedCheckActor;delete window.savedCheckActor;renderChecks();renderPlayGuidance(snapshot.state)});
  await b.locator('[data-resolve-check]').click();await b.locator('.check-request').waitFor({state:'detached'});
  await b.waitForFunction(()=>snapshot.state.messages.at(-1).check?.success===true);
  assert.match(await b.locator('#messages').textContent(),/contra CD 16: éxito/);
  assert.match(await b.locator('#messages .check-result').last().textContent(),/Éxito.*Fortaleza/);
  // A saved natural1 result remains a failure even if its total beats the DC.
  // This is a rendering probe; it does not roll or write to the campaign.
  await b.evaluate(()=>{const m=structuredClone(snapshot.state.messages.findLast(m=>m.check?.kind==='save'));m.check.die=1;m.check.modifier=20;m.check.total=21;m.check.dc=10;m.check.success=false;m.check.natural='fallo automático';snapshot.state.messages.push(m);render()});
  assert.match(await b.locator('#messages .check-result').last().textContent(),/Fallo.*Total 21 contra CD 10.*fallo automático/s);
  await b.evaluate(()=>{snapshot.state.messages.pop();render()});
  await a.reload();await a.locator('#app').waitFor({state:'visible'});assert.equal(await a.locator('.check-request').count(),0);
  // Saving a legacy-style sheet retains the new prepared skill totals.
  await b.locator('.party-person').click();
  assert.equal(await b.locator('[name=skillTotalsInput]').inputValue(),'Percepción | 8');
  await b.locator('#characterForm [name=skillTotalsInput]').fill('Percepción | 8\nSigilo | 5');
  await b.locator('#characterForm button.primary').click();await b.locator('#modal').waitFor({state:'hidden'});
  await b.locator('.party-person').click();await b.locator('.sheet-free-roll > summary').click();
  await b.locator('[data-sheet-selection]').selectOption('10');assert.equal(await b.locator('[data-check-key="Sigilo"]').textContent(),'Tirar Sigilo (+5)');
  await b.setViewportSize({width:390,height:844});
  await b.locator('.sheet-checks').scrollIntoViewIfNeeded();
  assert.equal(await b.locator('#modal').evaluate(el=>el.scrollWidth<=el.clientWidth),true);
  await b.screenshot({path:'.deps/checks-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);console.log('OK: sheet checks, stored modifiers, host request, player roll, automatic DC result, two-client persistence, skill editing and mobile. No AI.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
