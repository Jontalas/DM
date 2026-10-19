// Verify background polling without a browser or paid services.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

(async()=>{
 let calls=0,release,interval,visible;
 const app={hidden:false},document={hidden:false,addEventListener:(name,fn)=>{visible=fn}};
 const context=vm.createContext({token:'session',busy:false,document,$:()=>app,
  refresh:()=>{calls++;return new Promise(resolve=>{release=resolve})},
  setInterval:(fn,ms)=>{assert.equal(ms,15000);interval=fn},init:()=>{}});
 const script=fs.readFileSync('static/app.js','utf8');
 vm.runInContext(script.slice(script.indexOf('let syncing=false;')),context);
 document.hidden=true;await interval();assert.equal(calls,0);
 document.hidden=false;const pending=interval();await interval();assert.equal(calls,1);
 release();await pending;
 document.hidden=true;visible();assert.equal(calls,1);
 document.hidden=false;visible();assert.equal(calls,2);
 release();await new Promise(resolve=>setImmediate(resolve));
 app.hidden=true;await interval();assert.equal(calls,2);
 console.log('OK: hidden tabs pause, requests do not overlap, returning refreshes.');
})().catch(error=>{console.error(error);process.exitCode=1});
