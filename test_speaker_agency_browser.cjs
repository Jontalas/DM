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
  await guest.setViewportSize({width:390,height:1000});await guest.locator('#messageKind').selectOption('action');await guest.locator('#speaker').selectOption(actor);await guest.locator('#useAI').uncheck();await guest.locator('#message').fill('Elijo esperar');const version=await guest.evaluate(()=>snapshot.version);
  const delayedTalk=process.env.TEST_TALK_DELAYED_SUCCESS==='1',newDraft=process.env.TEST_TALK_SAME_DRAFT==='1'?'Elijo esperar':'Este borrador nuevo todavía no está enviado.';let talkSent,releaseTalk,sentBody;const talkRequested=new Promise(resolve=>{talkSent=resolve}),talkGate=new Promise(resolve=>{releaseTalk=resolve});
  const mirrorQuota=process.env.TEST_TALK_MIRROR_QUOTA==='1',quotaEdit=process.env.TEST_TALK_QUOTA_EDIT==='1',talkBodies=[];guest.on('request',request=>{if(request.url().endsWith('/api/action'))talkBodies.push(request.postDataJSON())});
  if(mirrorQuota)await guest.evaluate(()=>{window.quotaWriteHit=false;window.originalDraftStorage=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(key==='cronicas-pending'&&!window.quotaWriteHit){window.quotaWriteHit=true;throw new DOMException('Fixture quota','QuotaExceededError')}return window.originalDraftStorage.call(this,key,value)}});
  if(delayedTalk)await guest.route('**/api/action',async route=>{sentBody=route.request().postDataJSON();const response=await route.fetch();assert.equal(response.status(),200);talkSent();await talkGate;await route.fulfill({response})},{times:1});
  await guest.locator('#send').tap();
  let queuedBody;
  if(mirrorQuota){await guest.waitForFunction(()=>window.quotaWriteHit&&!busy);assert.equal(talkBodies.length,0);assert.equal(await guest.evaluate(()=>snapshot.version),version);await guest.evaluate(()=>{Storage.prototype.setItem=window.originalDraftStorage;delete window.originalDraftStorage});if(quotaEdit)await guest.locator('#message').fill('Nuevo borrador después del fallo de espacio.');await guest.locator('#send').tap();await guest.waitForFunction(()=>!busy&&!!localStorage.getItem('cronicas-pending'));queuedBody=await guest.evaluate(()=>JSON.parse(localStorage.getItem('cronicas-pending')).body);assert.equal(talkBodies.length,0);await guest.locator('#playGuidanceAction').tap()}
  if(delayedTalk){await talkRequested;await guest.locator('#message').fill('Edición intermedia.');await guest.locator('#message').fill(newDraft);await guest.locator('[data-tab=journal]').tap();releaseTalk()}
  await guest.waitForFunction(v=>snapshot.version>v&&!busy,version);
  if(mirrorQuota){assert.equal(talkBodies.length,1);assert.deepEqual(talkBodies[0],queuedBody);assert.equal(await guest.locator('#message').inputValue(),quotaEdit?'Nuevo borrador después del fallo de espacio.':'');assert.equal(await guest.evaluate(()=>snapshot.state.messages.filter(message=>message.text==='Elijo esperar').length),1)}
  else if(delayedTalk){assert.equal(await guest.locator('#message').inputValue(),newDraft,'A confirmed reply must preserve a draft edited while waiting');assert.equal(await guest.locator('#journal').evaluate(e=>e.classList.contains('active')),true);assert.equal(sentBody.text,'Elijo esperar');assert.equal(await guest.evaluate(()=>snapshot.state.messages.filter(m=>m.text==='Elijo esperar').length),1)}else assert.equal(await guest.locator('#message').inputValue(),'');
  assert.equal(await guest.evaluate(()=>snapshot.state.messages.at(-1).speaker),'Aria · Luis');
  console.log('Speaker agency verified: host action/dialogue excludes guest PC; administrative notes remain; kind changes reset selection locally with zero POST; owner sends on mobile. No AI.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
