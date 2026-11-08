const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{createInterface({input:fixture.stdout}).once('line',resolve);fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const host=await browser.newPage(),guest=await browser.newPage({hasTouch:true}),posts=[];
  await host.goto(url);await host.locator('#createForm [name=player]').fill('Ana');await host.locator('#createForm [name=goal]').fill('Explorar');await host.locator('#createForm button').click();
  await host.waitForFunction(()=>!!snapshot);
  const invite=await host.evaluate(()=>snapshot.invite);
  const joined=await guest.request.post(url+'/api/join',{data:{name:'Luis',invite}});assert.equal(joined.status(),200);const {token}=await joined.json();
  await guest.goto(url);await guest.evaluate(t=>localStorage.setItem('cronicas-token',t),token);await guest.reload();
  await guest.locator('[data-create-hero]').click();await guest.locator('[data-creator-preset=guardian]').click();await guest.locator('#creatorName').fill('Aria');await guest.locator('[data-creator-step="3"]').click();await guest.locator('#creatorFinish').click();await guest.locator('.sheet-checks').waitFor();await guest.locator('#closeModal').click();
  await host.evaluate(()=>refresh(true));const actor=await guest.evaluate(()=>snapshot.state.characters[0].id);
  host.on('request',r=>{if(r.method()==='POST')posts.push(r.url())});
  for(const kind of ['action','dialogue']){await host.locator('#messageKind').selectOption(kind);assert.equal(await host.locator(`#speaker option[value="${actor}"]`).count(),0)}
  for(const kind of ['ooc','private']){await host.locator('#messageKind').selectOption(kind);await host.locator('#speaker').selectOption(actor);await host.locator('#messageKind').selectOption('action');assert.equal(await host.locator('#speaker').inputValue(),'')}
  assert.deepEqual(posts,[]);
  await guest.setViewportSize({width:390,height:1000});await guest.locator('#messageKind').selectOption('action');await guest.locator('#speaker').selectOption(actor);await guest.locator('#useAI').uncheck();await guest.locator('#message').fill('Elijo esperar');const version=await guest.evaluate(()=>snapshot.version);await guest.locator('#send').tap();await guest.waitForFunction(v=>snapshot.version>v&&!busy,version);
  assert.equal(await guest.evaluate(()=>snapshot.state.messages.at(-1).speaker),'Aria · Luis');
  console.log('Speaker agency verified: host action/dialogue excludes guest PC; administrative notes remain; kind changes reset selection locally with zero POST; owner sends on mobile. No AI.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
