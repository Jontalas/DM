const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process');
const {createInterface}=require('node:readline');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
 const fixture=spawn(path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});
 let browser;
 try{
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});fixture.once('exit',()=>reject(Error('Fixture exited')))});
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext();
  const token=(await (await context.request.post(url+'/api/create',{data:{player:'Ana',title:'Reader test'}})).json()).token;
  await context.addInitScript(value=>localStorage.setItem('cronicas-token',value),token);
  const page=await context.newPage(),errors=[],images=[];let originals=0,writes=0;
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().includes('/book-pages/'))images.push(r.url());if(r.url().includes('/books/'))originals++;if(r.url().endsWith('/api/action'))writes++});
  const ready=async n=>{await page.waitForFunction(n=>!document.querySelector('#bookPageImage').hidden&&document.querySelector('#bookPageImage').alt.startsWith('Página '+n+' '),n)};
  const open=async n=>{await page.locator('#page').fill(String(n));await page.locator('#openPage').click();await ready(n)};
  await page.goto(url);await page.locator('#app').waitFor({state:'visible'});
  await page.locator('[data-tab="books"]').click();await ready(1);
  assert.equal(images.length,1);assert.equal(await page.locator('#bookPageImage').evaluate(el=>el.naturalWidth),180);
  await page.locator('#nextBookPage').click();await ready(2);assert.equal(images.length,2);
  await page.locator('#previousBookPage').click();await ready(1);assert.equal(images.length,2);
  await page.reload();await page.locator('#app').waitFor({state:'visible'});await page.locator('[data-tab="books"]').click();await ready(1);
  assert.equal(images.length,2);assert.match(await page.locator('#bookLoadStatus').textContent(),/copia guardada/);
  await page.locator('#readerZoomIn').click();assert.equal(await page.locator('#bookPageImage').evaluate(el=>el.style.width),'125%');
  await page.locator('#readerFit').click();await page.locator('#expandReader').click();assert.ok(await page.locator('body').evaluate(el=>el.classList.contains('reader-wide')));
  await page.locator('#expandReader').click();
  // A slow old request must never replace the more recently requested page.
  await page.evaluate(()=>bookReader.reset());
  let release,started;const gate=new Promise(resolve=>release=resolve),seen=new Promise(resolve=>started=resolve);
  await page.route('**/book-pages/**/1.jpg',async route=>{started();await gate;try{await route.continue()}catch{}});
  await page.locator('#openPage').click();await seen;
  await open(2);release();await page.unroute('**/book-pages/**/1.jpg');await page.waitForTimeout(150);
  assert.match(await page.locator('#bookPageImage').getAttribute('alt'),/^Página 2 /);
  // Invalid pages do not transfer an image; the reader can recover immediately.
  const count=images.length;await page.locator('#page').fill('999');await page.locator('#openPage').click();
  await page.waitForFunction(()=>document.querySelector('#bookLoadStatus').textContent.includes('tiene 2 páginas'));
  assert.equal(images.length,count);await open(1);
  await page.setViewportSize({width:390,height:844});await open(2);
  await page.locator('#expandReader').click();assert.equal(await page.locator('#composer').isVisible(),false);
  await page.locator('#bookPageImage').scrollIntoViewIfNeeded();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.equal(originals,0);assert.equal(writes,0);assert.deepEqual(errors,[]);
  await page.screenshot({path:'.deps/reader-mobile.png',fullPage:true});
  // Cached private pages are partitioned by session, even in the same tab.
  const second=(await (await context.request.post(url+'/api/create',{data:{player:'Luis',title:'Other session'}})).json()).token;
  const beforeSession=images.length;await page.evaluate(value=>{token=value},second);await open(2);
  assert.equal(images.length,beforeSession+1);
  // A new manifest revision cannot reuse the previous version's cached image.
  await page.route('**/api/book-info?book=reglas',route=>route.fulfill({json:{version:1,book:'reglas',pages:2,revision:'f'.repeat(32),format:'jpeg'}}));
  await page.route('**/book-pages/reglas/'+ 'f'.repeat(32)+'/*.jpg',route=>route.fulfill({path:path.resolve('test_fixtures/reader-1.jpg'),contentType:'image/jpeg'}));
  await page.evaluate(()=>bookReader.reset());const beforeRevision=images.length;await open(1);
  assert.equal(images.length,beforeRevision+1);assert.ok(images.at(-1).includes('f'.repeat(32)));
  assert.deepEqual(errors,[]);
  console.log('OK: requested pages only, browser reload cache, navigation, zoom, expanded reader, stale request cancellation, recovery and mobile; zero PDFs, AI or campaign writes.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
