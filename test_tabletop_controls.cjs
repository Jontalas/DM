const assert=require('node:assert/strict');
const {route}=require('./static/tabletop-controls.js');

// Every origin/destination pair on the board must yield a continuous grid route.
for(let x=0;x<20;x++)for(let y=0;y<20;y++)for(let tx=0;tx<20;tx++)for(let ty=0;ty<20;ty++){
 const path=route([x,y],[[tx,ty]]);
 assert.equal(path.length,Math.max(Math.abs(tx-x),Math.abs(ty-y)));
 let previous=[x,y];
 for(const point of path){
  assert.equal(Math.max(Math.abs(point[0]-previous[0]),Math.abs(point[1]-previous[1])),1);
  previous=point;
 }
 assert.deepEqual(previous,[tx,ty]);
}
assert.deepEqual(route([0,0],[[2,0],[2,2]]),[[1,0],[2,0],[2,1],[2,2]]);
assert.deepEqual(route([3,3],[[3,3]]),[]);
for(const point of [[20,0],[-1,0],[1.5,2],[null,2],[],[NaN,0]]){
 assert.throws(()=>route([0,0],[point]),/fuera/);
}
assert.throws(()=>route([0,0],Array.from({length:8},(_,i)=>[i%2?0:19,19])),/100/);
console.log('OK: 160000 grid routes, waypoints, continuity, bounds and route length.');
