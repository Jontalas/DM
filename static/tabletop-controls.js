/* Behavioral tabletop controls. Everything here is local until explicit confirmation. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.TabletopControls=api})(globalThis,function(){
 'use strict';
 function line(from,to){
  const result=[];let [x,y]=from;const [tx,ty]=to;
  const dx=Math.abs(tx-x),dy=-Math.abs(ty-y),sx=x<tx?1:-1,sy=y<ty?1:-1;let error=dx+dy;
  while(x!==tx||y!==ty){const twice=2*error;if(twice>=dy){error+=dy;x+=sx}if(twice<=dx){error+=dx;y+=sy}result.push([x,y])}
  return result;
 }
 function route(origin,points){
  for(const p of [origin,...points])if(!Array.isArray(p)||p.length!==2||p.some(n=>!Number.isInteger(n)||n<0||n>=20))throw Error('Punto fuera del tablero');
  let result=[],last=origin;
  for(const point of points){result.push(...line(last,point));last=point;if(result.length>100)throw Error('El recorrido supera 100 casillas')}
  return result;
 }
 function mount(options){
  const {scroller,grid,tool,zoom,snapshot,select,preview,measure,cancel,openSheet,tab,focusChat,notify}=options;
  let gesture=null,suppressUntil=0,lastChat=0,cellSize=Number(zoom.value);
  function ready(){return snapshot()&&!document.querySelector('#app').hidden&&!document.querySelector('dialog[open]')}
  function cellAt(event){
   const rect=grid.getBoundingClientRect(),cell=grid.firstElementChild;
   if(!cell)return null;
   const step=cell.getBoundingClientRect().width+parseFloat(getComputedStyle(grid).columnGap||0);
   const x=Math.floor((event.clientX-rect.left)/step),y=Math.floor((event.clientY-rect.top)/step);
   return x>=0&&y>=0&&x<20&&y<20?[x,y]:null;
  }
  function setTool(value){tool.value=value;tool.dispatchEvent(new Event('change'))}
  function changeZoom(value,clientX,clientY){
   const old=cellSize,next=Math.max(Number(zoom.min),Math.min(Number(zoom.max),value));
   const rect=scroller.getBoundingClientRect();
   const x=clientX===undefined?scroller.clientWidth/2:clientX-rect.left-scroller.clientLeft;
   const y=clientY===undefined?scroller.clientHeight/2:clientY-rect.top-scroller.clientTop;
   const gx=(scroller.scrollLeft+x)/(old+1),gy=(scroller.scrollTop+y)/(old+1);
   cellSize=next;zoom.value=String(next);document.documentElement.style.setProperty('--cell',next+'px');
   const output=document.querySelector('#zoomValue');if(output)output.textContent=Math.round(next/44*100)+'%';
   scroller.scrollLeft=gx*(next+1)-x;scroller.scrollTop=gy*(next+1)-y;
   options.repaint?.();
  }
  zoom.addEventListener('input',()=>changeZoom(Number(zoom.value)));
  zoom.addEventListener('dblclick',()=>changeZoom(44));
  function finish(clear=false){
   const previous=gesture;gesture=null;scroller.classList.remove('panning','dragging-token');
   if(previous&&scroller.hasPointerCapture(previous.pointerId))scroller.releasePointerCapture(previous.pointerId);
   if(clear)cancel();
  }
  scroller.addEventListener('contextmenu',event=>event.preventDefault());
  scroller.addEventListener('pointerdown',event=>{
   if(!ready()||gesture)return;
   if(event.button===2||(event.button===0&&tool.value==='pan')){
    gesture={kind:'pan',pointerId:event.pointerId,x:event.clientX,y:event.clientY,left:scroller.scrollLeft,top:scroller.scrollTop};
    scroller.setPointerCapture(event.pointerId);scroller.classList.add('panning');event.preventDefault();return;
   }
   if(event.button!==0)return;
   const point=cellAt(event);if(!point)return;
   if(tool.value==='measure'){
    gesture={kind:'measure',pointerId:event.pointerId,x:event.clientX,y:event.clientY,origin:point,active:false};return;
   }
   if(tool.value!=='move')return;
   const data=snapshot(),c=data.state.characters.find(c=>c.x===point[0]&&c.y===point[1]);
   if(!c||(!data.me.host&&c.owner!==data.me.id))return;
   gesture={kind:'token',pointerId:event.pointerId,x:event.clientX,y:event.clientY,origin:point,id:c.id,anchors:[],hover:point,active:false};
  });
  scroller.addEventListener('pointermove',event=>{
   const g=gesture;if(!g||g.pointerId!==event.pointerId)return;
   if(g.kind==='pan'){scroller.scrollLeft=g.left+g.x-event.clientX;scroller.scrollTop=g.top+g.y-event.clientY;event.preventDefault();return}
   if(!g.active&&Math.hypot(event.clientX-g.x,event.clientY-g.y)<5)return;
   const point=cellAt(event);if(!point)return;
   if(!g.active){g.active=true;scroller.setPointerCapture(event.pointerId);if(g.kind==='token'){select(g.id);scroller.classList.add('dragging-token')}}
   if(g.kind==='measure'){measure([g.origin,point]);event.preventDefault();return}
   const current=snapshot().state.characters.find(c=>c.id===g.id);
   if(!current||current.x!==g.origin[0]||current.y!==g.origin[1]){finish(true);notify('La ficha cambió durante el arrastre. Vuelve a seleccionarla.');return}
   g.hover=point;
   try{preview(route(g.origin,[...g.anchors,point]))}catch(error){notify(error.message)}
   event.preventDefault();
  });
  scroller.addEventListener('pointerup',event=>{
   if(!gesture||gesture.pointerId!==event.pointerId)return;
   if(gesture.kind==='pan'||gesture.active)suppressUntil=Date.now()+150;
   finish();
  });
  scroller.addEventListener('pointercancel',()=>finish(true));
  scroller.addEventListener('lostpointercapture',event=>{if(event.target===scroller&&gesture)finish(true)});
  window.addEventListener('blur',()=>{if(gesture)finish(true)});
  scroller.addEventListener('click',event=>{if(event.detail&&Date.now()<suppressUntil){event.preventDefault();event.stopImmediatePropagation()}},true);
  scroller.addEventListener('dblclick',event=>{
   if(tool.value!=='move'||!ready())return;
   const point=cellAt(event),data=snapshot();if(!point)return;
   const c=data.state.characters.find(c=>c.x===point[0]&&c.y===point[1]);
   if(c&&(data.me.host||c.owner===data.me.id))openSheet(c.id);
  });
  scroller.addEventListener('wheel',event=>{
   if(!ready())return;
   if(event.altKey||event.ctrlKey||event.metaKey){event.preventDefault();changeZoom(Number(zoom.value)+(event.deltaY<0?4:-4),event.clientX,event.clientY)}
   else if(event.shiftKey){event.preventDefault();scroller.scrollLeft+=event.deltaY||event.deltaX}
  },{passive:false});
  document.addEventListener('keydown',event=>{
   if(!ready()||event.ctrlKey||event.metaKey||event.altKey||event.target.closest('input,textarea,select,[contenteditable=true]'))return;
   const key=event.key.toLowerCase();
   if(key==='escape'){if(gesture)suppressUntil=Date.now()+150;finish(true);event.preventDefault();return}
   if(key===' '&&gesture?.kind==='token'&&gesture.active){
    if(!event.repeat&&gesture.anchors.length<20)gesture.anchors.push([...gesture.hover]);
    event.preventDefault();return;
   }
   if(gesture)return;
   const tools={s:'move',a:'pan',q:'measure'};
   if(tools[key]){setTool(tools[key]);event.preventDefault()}
   else if(key==='+'||key==='='||key==='-'){changeZoom(Number(zoom.value)+(key==='-'?-4:4));event.preventDefault()}
   else if(key==='c'){tab('story');if(Date.now()-lastChat<500)focusChat();lastChat=Date.now();event.preventDefault()}
   else if(key==='j'){tab('journal');event.preventDefault()}
   else if(key==='d'){tab('dice');event.preventDefault()}
  });
  return {changeZoom};
 }
 return {line,route,mount};
});
