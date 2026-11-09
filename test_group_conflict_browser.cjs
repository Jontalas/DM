const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const hostContext=await browser.newContext({hasTouch:true}),guestContext=await browser.newContext({hasTouch:true});
  const host=await hostContext.newPage(),guest=await guestContext.newPage(),actions=[],errors=[];
  for(const page of [host,guest]){page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))actions.push({page:page===host?'host':'guest',body:r.postDataJSON()})})}
  const hero=async(page,name)=>{await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill(name);await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click()};
  await host.goto(url);await host.locator('#createForm [name=player]').fill('Ana');await host.locator('#createForm [name=goal]').fill('Investigar juntos la posada');await host.locator('#createForm [name=mode]').selectOption('online');await host.locator('#createForm button').click();await hero(host,'Liria');
  const invite=await host.evaluate(()=>snapshot.invite);
  await guest.goto(url+'/?invite='+encodeURIComponent(invite));await guest.locator('#joinForm [name=name]').fill('Luis');await guest.locator('#joinForm button').click();await hero(guest,'Taro');
  await host.reload();await host.waitForFunction(()=>snapshot?.state.characters.length===2&&!busy);
  const hostId=await host.evaluate(()=>snapshot.state.characters.find(c=>c.owner===snapshot.me.id).id),guestId=await guest.evaluate(()=>snapshot.state.characters.find(c=>c.owner===snapshot.me.id).id);
  assert.notEqual(hostId,guestId);
  await host.locator('#messageKind').selectOption('private');await host.locator('#message').fill('PRIVATE-ANA-NOTE');await host.locator('#send').click();await host.waitForFunction(()=>!busy&&!document.querySelector('#message').value);
  await guest.reload();await guest.waitForFunction(()=>snapshot?.state.characters.length===2&&!busy);
  assert.doesNotMatch(JSON.stringify(await guest.evaluate(()=>snapshot)),/PRIVATE-ANA-NOTE/);
  const choices=await guest.locator('#speaker option').evaluateAll(items=>items.map(e=>e.value));assert.ok(choices.includes(guestId));assert.ok(!choices.includes(hostId));
  let freeze=true;
  await guest.route('**/api/state?*',async route=>{if(freeze)return route.fulfill({json:{unchanged:true}});await route.continue()});
  await guest.locator('#messageKind').selectOption('ooc');await guest.locator('#useAI').uncheck();await guest.locator('#message').fill('Mi decisión sigue pendiente.');
  await host.locator('#messageKind').selectOption('ooc');await host.locator('#useAI').uncheck();await host.locator('#message').fill('La mesa tiene una novedad.');await host.locator('#send').click();await host.waitForFunction(()=>!busy&&!document.querySelector('#message').value);
  const before=actions.length;
  await guest.locator('#send').focus();await guest.keyboard.press('Enter');await guest.waitForFunction(()=>!busy&&document.querySelector('#toast').textContent.includes('Revisa tu acción'));
  assert.equal(await guest.locator('#message').inputValue(),'Mi decisión sigue pendiente.');assert.equal(await guest.evaluate(()=>localStorage.getItem('cronicas-pending')),null);
  assert.equal(actions.length,before+1);assert.equal(actions.at(-1).body.director,false);
  const rejected=actions.at(-1).body;
  assert.ok(!(await guest.evaluate(()=>snapshot.state.messages)).some(m=>m.text==='Mi decisión sigue pendiente.'));
  freeze=false;await guest.locator('#send').click();await guest.waitForFunction(()=>!busy&&!document.querySelector('#message').value);
  assert.notEqual(actions.at(-1).body.id,rejected.id);assert.ok(actions.at(-1).body.version>rejected.version);
  await host.reload();await host.waitForFunction(()=>snapshot?.state.messages.some(m=>m.text==='Mi decisión sigue pendiente.')&&!busy);
  assert.equal((await host.evaluate(()=>snapshot.state.messages)).filter(m=>m.text==='Mi decisión sigue pendiente.').length,1);
  await guest.reload();await guest.waitForFunction(()=>snapshot?.state.messages.some(m=>m.text==='Mi decisión sigue pendiente.')&&!busy);
  assert.doesNotMatch(JSON.stringify(await guest.evaluate(()=>snapshot)),/PRIVATE-ANA-NOTE/);
  await guest.setViewportSize({width:390,height:1000});await guest.locator('[data-tab=story]').tap();assert.ok(await guest.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.ok(!actions.some(a=>a.body.director===true));assert.deepEqual(errors,[]);
  console.log('Two-participant GUI: legal owned characters, private note isolation, stale action rejected with text retained, explicit resubmission once, shared result after reload, keyboard/mobile; zero inference. Not group campaign certification.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
