const {chromium}=require('./.deps/browser-tests/node_modules/playwright');
const {spawn}=require('node:child_process');
const {createInterface}=require('node:readline');
const path=require('node:path');
const assert=require('node:assert/strict');

(async()=>{
 const fixture=spawn(process.env.TEST_PYTHON||path.resolve('.venv/Scripts/python.exe'),['test_browser_fixture.py'],{stdio:['ignore','pipe','inherit']});
 let browser;
 try{
  const url=await new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>reject(Error('Fixture timeout')),15000);
   fixture.once('exit',code=>{clearTimeout(timer);reject(Error('Fixture exited: '+code))});
   createInterface({input:fixture.stdout}).once('line',line=>{clearTimeout(timer);resolve(line)});
  });
  browser=await chromium.launch({headless:true,executablePath:process.env.TEST_BROWSER||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const host=await browser.newContext(),guest=await browser.newContext({hasTouch:true});
  const token=(await (await host.request.post(url+'/api/create',{data:{player:'Ana',title:'Gestos de mesa'}})).json()).token;
  const hostHeaders={Authorization:'Bearer '+token};
  const room=await (await host.request.get(url+'/api/state',{headers:hostHeaders})).json();
  const guestToken=(await (await guest.request.post(url+'/api/join',{data:{name:'Luis',invite:room.invite}})).json()).token;
  const headers={Authorization:'Bearer '+guestToken};
  async function saved(){return (await guest.request.get(url+'/api/state',{headers})).json()}
  const person=(await saved()).me;
  for(const [name,enemy] of [['Aria',false],['Bandido',true]]){
   const row=await saved();
   const response=await host.request.post(url+'/api/action',{headers:hostHeaders,data:{id:name,version:row.version,type:'character',character:{name,enemy,owner:enemy?room.me.id:person.id}}});
   assert.equal(response.ok(),true);
  }
  await guest.addInitScript(value=>localStorage.setItem('cronicas-token',value),guestToken);
  const page=await guest.newPage(),errors=[];let writes=0;
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{if(request.url().endsWith('/api/action'))writes++});
  await page.goto(url);await page.locator('#app').waitFor({state:'visible'});
  const before=await saved();
  const cell=(x,y)=>page.locator(`.cell[data-x="${x}"][data-y="${y}"]`);
  const center=async locator=>{const box=await locator.boundingBox();return {x:box.x+box.width/2,y:box.y+box.height/2}};
  const scroll=page.locator('.board-scroll');
  // Drag prepares a continuous route; Escape cancels it without saving.
  await cell(0,0).dragTo(cell(2,1));
  assert.equal(await page.locator('#grid .path').count(),2);
  assert.equal((await saved()).version,before.version);
  await page.keyboard.press('Escape');assert.equal(await page.locator('#grid .path').count(),0);
  // Space fixes a waypoint and produces a different route from a direct diagonal.
  let start=await center(cell(0,0)),waypoint=await center(cell(0,2)),end=await center(cell(3,2));
  await page.mouse.move(start.x,start.y);await page.mouse.down();
  await page.mouse.move(waypoint.x,waypoint.y,{steps:5});await page.keyboard.press('Space');
  await page.mouse.move(end.x,end.y,{steps:5});await page.mouse.up();
  assert.equal(await page.locator('#grid .path').count(),5);
  await page.keyboard.press('Escape');
  // Measurement can be dragged; it draws an overlay and never moves the token.
  await page.locator('#tool').selectOption('measure');await cell(0,0).dragTo(cell(3,2));
  assert.match(await page.locator('#pathInfo').textContent(),/20 pies/);
  assert.equal(await page.locator('.ruler-overlay line').count(),1);
  const rulerEnd=await page.locator('.ruler-overlay line').getAttribute('x2');
  await page.locator('#zoom').focus();await page.keyboard.press('ArrowRight');
  assert.ok(Number(await page.locator('.ruler-overlay line').getAttribute('x2'))>Number(rulerEnd));
  await page.locator('#zoom').dblclick();
  await page.locator('#tool').selectOption('move');
  // Right-button panning changes the camera, not character coordinates.
  await scroll.evaluate(el=>{el.scrollLeft=100;el.scrollTop=100});
  let box=await scroll.boundingBox();
  await page.mouse.move(box.x+200,box.y+80);await page.mouse.down({button:'right'});
  await page.mouse.move(box.x+150,box.y+40,{steps:5});await page.mouse.up({button:'right'});
  assert.equal(await scroll.evaluate(el=>el.scrollLeft>=149&&el.scrollTop>=139),true);
  // The local hand tool provides the same pan without requiring a right button.
  await page.locator('#tool').selectOption('pan');
  await page.mouse.move(box.x+200,box.y+80);await page.mouse.down();
  await page.mouse.move(box.x+175,box.y+60,{steps:5});await page.mouse.up();
  assert.equal(await scroll.evaluate(el=>el.scrollLeft>=174&&el.scrollTop>=159),true);
  await scroll.evaluate(el=>{el.scrollLeft=0;el.scrollTop=0});
  await page.locator('#tool').selectOption('move');
  // Wheel zoom and reset stay local.
  const oldZoom=Number(await page.locator('#zoom').inputValue());
  const anchorBefore=await scroll.evaluate(el=>[(el.scrollLeft+199)/45,(el.scrollTop+79)/45]);
  await page.mouse.move(box.x+200,box.y+80);await page.keyboard.down('Alt');await page.mouse.wheel(0,-100);await page.keyboard.up('Alt');
  await page.waitForFunction(value=>Number(document.querySelector('#zoom').value)>value,oldZoom);
  const anchorAfter=await scroll.evaluate(el=>{const size=Number(document.querySelector('#zoom').value)+1;return [(el.scrollLeft+199)/size,(el.scrollTop+79)/size]});
  assert.ok(Math.abs(anchorBefore[0]-anchorAfter[0])<0.05&&Math.abs(anchorBefore[1]-anchorAfter[1])<0.05);
  await page.locator('#zoom').dblclick();assert.equal(await page.locator('#zoom').inputValue(),'44');
  await scroll.evaluate(el=>{el.scrollLeft=0;el.scrollTop=0});
  // Double click inspects the controlled character.
  await cell(0,0).dblclick();await page.locator('#characterForm').waitFor();
  assert.equal(await page.locator('#characterForm [name=name]').inputValue(),'Aria');
  await page.locator('#closeModal').click();
  // Keyboard tool/panel shortcuts are ignored while typing in chat.
  await page.locator('#turnInfo').click();await page.keyboard.press('a');
  assert.equal(await page.locator('#tool').inputValue(),'pan');
  await page.keyboard.press('s');assert.equal(await page.locator('#tool').inputValue(),'move');
  await page.keyboard.press('q');assert.equal(await page.locator('#tool').inputValue(),'measure');
  await page.keyboard.press('j');assert.equal(await page.locator('#journal').isVisible(),true);
  await page.keyboard.press('d');assert.equal(await page.locator('#dice').isVisible(),true);
  await page.keyboard.press('c');await page.keyboard.press('c');
  assert.equal(await page.locator('#message').evaluate(el=>el===document.activeElement),true);
  await page.keyboard.type('sad');assert.equal(await page.locator('#message').inputValue(),'sad');
  assert.equal(await page.locator('#tool').inputValue(),'measure');
  await page.locator('#message').fill('');await page.locator('#turnInfo').click();
  assert.equal(writes,0);assert.equal((await saved()).version,before.version);
  // A confirmed drop route is one action validated by the existing server engine.
  await page.locator('#tool').selectOption('move');await cell(0,0).dragTo(cell(2,1));
  page.once('dialog',dialog=>dialog.accept());await page.locator('#confirmMove').click();
  await page.waitForFunction(()=>document.querySelector('.cell[data-x="2"][data-y="1"] .token')!==null);
  const after=await saved();assert.equal(after.version,before.version+1);assert.equal(writes,1);
  const hero=after.state.characters.find(c=>c.name==='Aria');assert.deepEqual([hero.x,hero.y],[2,1]);
  await cell(1,0).dragTo(cell(4,2));
  const unchanged=await saved();assert.equal(unchanged.version,after.version);
  assert.equal(unchanged.state.characters.find(c=>c.name==='Bandido').x,1);
  // GM double-click must also work on a token that was not already selected.
  await host.addInitScript(value=>localStorage.setItem('cronicas-token',value),token);
  const gmPage=await host.newPage();gmPage.on('pageerror',error=>errors.push(error.message));
  await gmPage.goto(url);await gmPage.locator('#app').waitFor({state:'visible'});
  await gmPage.locator('.cell[data-x="1"][data-y="0"]').dblclick();
  await gmPage.locator('#characterForm').waitFor();
  assert.equal(await gmPage.locator('#characterForm [name=name]').inputValue(),'Bandido');
  await gmPage.close();
  // The same preview works with a touch pointer on a narrow viewport.
  await page.setViewportSize({width:390,height:844});
  await page.locator('[data-tab=board]').click();
  await cell(2,1).scrollIntoViewIfNeeded();
  start=await center(cell(2,1));end=await center(cell(3,2));
  const touch=await guest.newCDPSession(page);
  await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:start.x,y:start.y,id:1}]});
  await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:end.x,y:end.y,id:1}]});
  await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  assert.equal(await page.locator('#grid .path').count(),1);
  assert.equal((await saved()).version,after.version);assert.equal(writes,1);
  await page.keyboard.press('Escape');
  await page.locator('#tool').selectOption('measure');
  await scroll.evaluate(el=>{el.scrollLeft=0;el.scrollTop=0});
  start=await center(cell(0,0));end=await center(cell(3,2));
  await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:start.x,y:start.y,id:1}]});
  await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:end.x,y:end.y,id:1}]});
  await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  assert.match(await page.locator('#pathInfo').textContent(),/20 pies/);
  assert.equal(await page.locator('.ruler-overlay line').count(),1);
  assert.equal(writes,1);assert.equal((await saved()).version,after.version);
  await touch.detach();
  assert.deepEqual(errors,[]);
  await page.screenshot({path:'.deps/tabletop-gestures.png',fullPage:true});
  console.log('OK: drag, waypoints, ruler, pan, zoom, shortcuts, typing, sheet, permissions, mobile touch, zero local writes and one confirmed move.');
 }finally{if(browser)await browser.close();fixture.kill()}
})().catch(error=>{console.error(error);process.exitCode=1});
