/* Development-only: extract and visually inspect cached official Cairn 1e tables.
 * No network requests; source cache is private .deps, not a runtime dependency.
 */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const {chromium}=require('../.deps/browser-tests/node_modules/playwright');
const groups=[['female-names','male-names','surnames','background'],
 ['physique','skin','hair','face','speech'],['clothing','virtue','vice','reputation','misfortunes'],
 ['armor','helmets--shields','weapons','bonus-item-roll-on-table-indicated'],
 ['expeditionary-gear','tools','trinkets'],['spellbooks-d100'],['armor-1','weapons-1']];
const traits=new Set(groups[1].concat(groups[2])),visualOnly=new Set(['armor-1','weapons-1']);
(async()=>{
 const source=path.resolve('.deps/rules-sources/cairn-1e-srd.html');
 const hash=crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex');
 const manifest=JSON.parse(fs.readFileSync('rules_sources/cairn-1e.json','utf8'));
 if(hash!==manifest.html_snapshot.sha256)throw Error('Official HTML snapshot does not match recorded hash');
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1000,height:800}});
  await page.route('http**/*',r=>r.abort());
  await page.goto(pathToFileURL(source).href);
  const tables=await page.evaluate(ids=>Object.fromEntries(ids.map(id=>{
   const heading=document.getElementById(id);
   const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_ELEMENT);
   walker.currentNode=heading;let table;
   while(walker.nextNode()){if(walker.currentNode.tagName==='TABLE'){table=walker.currentNode;break}}
   if(!table)throw Error('Missing table: '+id);
   return [id,{html:heading.outerHTML+table.outerHTML,rows:[...table.rows].map(r=>[...r.cells].map(c=>c.textContent.trim()))}];
  })),groups.flat());
  const result={source:'https://cairnrpg.com/first-edition/cairn-srd/',author:'Yochai Gal',license:'CC-BY-SA-4.0',
   licenseUrl:'https://creativecommons.org/licenses/by-sa/4.0/',sourceHtmlSha256:hash,
   changes:'Selected table cells indexed by die result; original English values retained.',tables:{}};
  for(const [id,table] of Object.entries(tables)){
   if(visualOnly.has(id))continue;
   const entries={};
   if(groups[3].includes(id)){
    const [ranges,values]=table.rows;
    ranges.forEach((range,i)=>{
     if(!/^\d+(?:-\d+)?$/.test(range))throw Error('Unexpected range: '+id+' '+range);
     const [lo,hi=lo]=range.split('-').map(Number);
     for(let n=lo;n<=hi;n++){if(entries[n])throw Error('Overlapping range: '+id);entries[n]=values[i]}
    });
   }
   else{
   for(const row of table.rows)for(let n=0;n<row.length;n+=2)if(/^\d+$/.test(row[n])){
    if(entries[row[n]]||!row[n+1])throw Error('Duplicate or empty table result: '+id);
    entries[row[n]]=row[n+1];
   }
   }
   const count=traits.has(id)?10:id==='spellbooks-d100'?100:20;
   if(Object.keys(entries).length!==count||Array.from({length:count},(_,i)=>i+1).some(n=>!entries[n]))throw Error('Incomplete table: '+id);
   result.tables[id]=Array.from({length:count},(_,i)=>entries[i+1]);
  }
  for(let i=0;i<groups.length;i++){
   await page.setContent('<html><head><meta charset="utf-8"><style>body{font:18px sans-serif;padding:20px;color:#111;background:white}table{border-collapse:collapse;width:100%;margin-bottom:24px}td,th{border:1px solid #aaa;padding:7px;text-align:left}h4{margin:12px 0}</style></head><body>'+groups[i].map(id=>tables[id].html).join('')+'</body></html>');
   await page.locator('svg').evaluateAll(es=>es.forEach(e=>e.remove())); // Remove decorative permalink icons only.
   await page.screenshot({path:'.deps/cairn-original-tables-'+(i+1)+'.png',fullPage:true});
  }
  fs.writeFileSync('systems/cairn_1e_tables.json',JSON.stringify(result,null,2)+'\n');
  console.log('Extracted '+Object.keys(result.tables).length+' original tables; '+groups.length+' visual evidence images saved. No network requests.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
