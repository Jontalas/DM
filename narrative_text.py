"""Repair complete UTF-8 byte sequences mistakenly emitted as legacy characters.

Only used for model-authored prose, never player input, identifiers or source books.
Mixed healthy Unicode stays intact; incomplete and ambiguous sequences stay intact.
"""
import copy


def _legacy_byte(character):
    try:return character.encode('cp1252')[0]
    except UnicodeEncodeError:
        value=ord(character)
        return value if 0x80<=value<=0x9f else None


def repair_text(value):
    if not isinstance(value,str):return value
    # At most two passes also handle common double-encoding, without unbounded work.
    for _ in range(2):
        result=[];i=0;changed=False
        while i<len(value):
            lead=_legacy_byte(value[i])
            size=2 if lead is not None and 0xc2<=lead<=0xdf else 3 if lead is not None and 0xe0<=lead<=0xef else 4 if lead is not None and 0xf0<=lead<=0xf4 else 0
            if size and i+size<=len(value):
                chunk=[_legacy_byte(c) for c in value[i:i+size]]
                if all(b is not None and 0x80<=b<=0xbf for b in chunk[1:]):
                    try:decoded=bytes(chunk).decode('utf-8')
                    except UnicodeDecodeError:decoded=None
                    if decoded is not None:
                        result.append(decoded);i+=size;changed=True;continue
            result.append(value[i]);i+=1
        fixed=''.join(result)
        if not changed:return value
        value=fixed
    return value


def normalize_response(result):
    """Leave IDs, schema keys, dice and references untouched."""
    output=copy.deepcopy(result)
    if not isinstance(output,dict):return output
    if 'narration' in output:output['narration']=repair_text(output['narration'])
    for item in output.get('proposals',[]) if isinstance(output.get('proposals'),list) else []:
        if isinstance(item,dict) and 'reason' in item:item['reason']=repair_text(item['reason'])
    for item in output.get('checks',[]) if isinstance(output.get('checks'),list) else []:
        if isinstance(item,dict) and 'reason' in item:item['reason']=repair_text(item['reason'])
    memory=output.get('memory')
    if isinstance(memory,dict):
        for key in ('summary','location','goal','preparation'):
            if key in memory:memory[key]=repair_text(memory[key])
        if isinstance(memory.get('objectives'),list):memory['objectives']=[repair_text(v) for v in memory['objectives']]
    module=output.get('adventureModule')
    if isinstance(module,dict):
        for key in ('title','premise','location','description','goal','preparation','conclusion'):
            if key in module:module[key]=repair_text(module[key])
        for collection,fields in [('opportunities',('label','discovery','failure')),('objectives',('text',))]:
            for item in module.get(collection,[]) if isinstance(module.get(collection),list) else []:
                if isinstance(item,dict):
                    for key in fields:
                        if key in item:item[key]=repair_text(item[key])
    return output
