const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{createInterface({input:fixture.stdout}).once('line',resolve);fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});const page=await browser.newPage({hasTouch:true}),posts=[],errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/action'))posts.push(r.postDataJSON())});
  await page.goto(url);await page.locator('#createForm [name=player]').fill('Ana');await page.locator('#createForm [name=goal]').fill('Comentar sin actuar inconsciente');await page.locator('#createForm button').click();
  await page.locator('[data-create-hero]').click();await page.locator('[data-creator-preset=guardian]').click();await page.locator('#creatorName').fill('Aria');await page.locator('[data-creator-step="3"]').click();await page.locator('#creatorFinish').click();await page.locator('.sheet-checks').waitFor();await page.locator('#closeModal').click();
  const actor=await page.evaluate(()=>snapshot.state.characters[0].id);
  // Explicit isolated test setup through the normal, audited correction API.
  await page.evaluate(async id=>act('manual',{character:id,hpDelta:-17,reason:'Estado técnico de prueba',resolution:'PJ inconsciente para verificar el compositor'}),actor);
  await page.setViewportSize({width:390,height:1000});const count=posts.length;
  for(const kind of ['action','dialogue']){
   await page.locator('#messageKind').selectOption(kind);
   for(const speaker of ['',actor]){await page.locator('#speaker').selectOption(speaker);assert.equal(await page.locator('#send').isDisabled(),true);assert.match(await page.locator('#aiHint').textContent(),/Fuera de personaje/);assert.equal(await page.locator('#message').getAttribute('aria-describedby'),'aiHint')}
  }
  await page.locator('#message').fill('Me levanto');await page.locator('#message').focus();await page.keyboard.press('Control+Enter');assert.equal(posts.length,count);
  await page.locator('#messageKind').selectOption('ooc');assert.equal(await page.locator('#send').isEnabled(),true);await page.locator('#message').fill('Comentario fuera de personaje');const version=await page.evaluate(()=>snapshot.version);await page.locator('#send').tap();await page.waitForFunction(v=>snapshot.version>v&&!busy,version);assert.equal(posts.length,count+1);assert.equal(posts.at(-1).kind,'ooc');assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hp),-1);
  await page.evaluate(async id=>act('manual',{character:id,hpDelta:1,reason:'Estado técnico de prueba',resolution:'PJ a0PG consciente'}),actor);
  await page.locator('#messageKind').selectOption('dialogue');await page.locator('#speaker').selectOption(actor);assert.equal(await page.locator('#send').isEnabled(),true);await page.locator('#message').fill('¿Puedes escucharme?');const next=await page.evaluate(()=>snapshot.version);await page.locator('#send').tap();await page.waitForFunction(v=>snapshot.version>v&&!busy,next);assert.equal(await page.evaluate(()=>snapshot.state.characters[0].hp),0);assert.equal(await page.locator('#send').isEnabled(),true);
  assert.deepEqual(errors,[]);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));console.log('Conversation health: unconscious default/explicit actor blocks locally and Ctrl+Enter sends nothing; accessible mobile hint, out-of-character note allowed, zero-HP dialogue free, final busy state restored. No AI.');
 }finally{await browser?.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
