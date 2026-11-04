const assert=require('node:assert/strict'),pdf=require('./static/rule-source-pdf');
assert.deepEqual(pdf.parsePages(' 3,1-2, 2 ',4),[1,2,3]);
for(const value of ['', '0','5','2-1','1-2000000','1,,2','1.5','1e2','-1','1/2','9007199254740993'])assert.throws(()=>pdf.parsePages(value,4));
assert.throws(()=>pdf.parsePages('1-32,33',100));
assert.equal(pdf.textFromItems([{str:'A',hasEOL:false},{str:'B',hasEOL:true},{str:'C',hasEOL:false}]),'A B\nC');
assert.throws(()=>pdf.textFromItems([{str:'   '}]),/OCR/);
assert.throws(()=>pdf.textFromItems([{str:'x'.repeat(24001)}]));
console.log('PDF selection: ranges, deduplication, limits, extraction order, missing text and oversized pages passed.');
