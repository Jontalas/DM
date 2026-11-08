"""Select whole narrative notes locally; retain full records in durable capture."""
import copy
import json
import re
import campaign_world as world

FORMAT='cronicas-campaign-world-context-1'
SELECTION_FORMAT='cronicas-world-note-selection-1'
MAX_BYTES=20000
SMALL_BYTES=6000
MAX_ENTITIES=6
MAX_RELATIONSHIPS=4
KINDS=('npcs','places','relationships')


def size(value):return len(json.dumps(value,ensure_ascii=False).encode('utf-8'))


def _words(value):return ' '.join(re.findall(r'\w+',value.casefold())) if isinstance(value,str) else ''


def _mentions(text,value):
    value=_words(value)
    return bool(value and ' '+value+' ' in ' '+text+' ')


def select(record,text,location):
    record=world.validate(record)
    if size(record)<=SMALL_BYTES:return record,None
    index={kind:[{key:item[key] for key in (('id','from','to','known') if kind=='relationships' else ('id','name','known'))} for item in record[kind]] for kind in KINDS}
    view={'format':FORMAT,'revision':record['revision'],'identities':index,'npcs':[],'places':[],'relationships':[],
        'omitted':{kind:len(record[kind]) for kind in KINDS}}
    selection={'format':SELECTION_FORMAT,**{kind:[] for kind in KINDS}}
    query,current=_words(text),_words(location)
    entries=[(kind,item) for kind in ('npcs','places') for item in record[kind]]
    priority={}
    for kind,item in entries:
        endpoint=('npc:' if kind=='npcs' else 'place:')+item['id']
        if _mentions(query,item['name']) or _mentions(query,item['id']):priority[endpoint]=0
        elif kind=='places' and _mentions(current,item['name']):priority[endpoint]=1
    # One ring around the entities actually named/current, without expanding
    # across the entire graph. Full endpoint identities always remain available.
    seeds=set(priority)
    for link in record['relationships']:
        if link['from'] in seeds or link['to'] in seeds:
            for endpoint in (link['from'],link['to']):priority.setdefault(endpoint,2)
    for kind,limit in (('npcs',2),('places',1)):
        for item in [item for item in record[kind] if item['known']][-limit:]:
            priority.setdefault(('npc:' if kind=='npcs' else 'place:')+item['id'],3)
    ranked=sorted(enumerate(entries),key=lambda pair:(priority.get(('npc:' if pair[1][0]=='npcs' else 'place:')+pair[1][1]['id'],9),pair[0]))

    def include(kind,item):
        candidate=copy.deepcopy(view);chosen=copy.deepcopy(selection)
        candidate[kind].append(item);candidate['omitted'][kind]-=1;chosen[kind].append(item['id'])
        if size({'notes':candidate,'selection':chosen})>MAX_BYTES:return False
        view.clear();view.update(candidate);selection.clear();selection.update(chosen);return True

    for _,(kind,item) in ranked:
        endpoint=('npc:' if kind=='npcs' else 'place:')+item['id']
        if endpoint not in priority:continue
        if len(selection['npcs'])+len(selection['places'])>=MAX_ENTITIES:break
        include(kind,item)
    selected={'npc:'+identifier for identifier in selection['npcs']}|{'place:'+identifier for identifier in selection['places']}
    links=sorted(enumerate(record['relationships']),key=lambda pair:(0 if pair[1]['from'] in seeds or pair[1]['to'] in seeds else 1,pair[0]))
    for _,link in links:
        if len(selection['relationships'])>=MAX_RELATIONSHIPS:break
        if link['from'] in selected or link['to'] in selected:include('relationships',link)
    # Never inflate a small/sparse record just to use the projection format.
    if size({'notes':view,'selection':selection})>=size(record):return record,None
    if size({'notes':view,'selection':selection})>MAX_BYTES:raise ValueError('El índice de memoria supera su límite de contexto')
    return view,selection


def validate_selection(record,selection):
    if selection is None:return
    record=world.validate(record)
    if (not isinstance(selection,dict) or set(selection)!={'format',*KINDS} or selection['format']!=SELECTION_FORMAT
        or any(not isinstance(selection[kind],list) or any(not isinstance(identifier,str) for identifier in selection[kind]) for kind in KINDS)
        or sum(len(selection[kind]) for kind in ('npcs','places'))>MAX_ENTITIES or len(selection['relationships'])>MAX_RELATIONSHIPS):
        raise ValueError('Selección de notas del mundo inválida')
    for kind in KINDS:
        if len(set(selection[kind]))!=len(selection[kind]) or not set(selection[kind])<={item['id'] for item in record[kind]}:
            raise ValueError('La selección no corresponde a las notas existentes')


def validate_updates(record,updates,selection):
    validate_selection(record,selection)
    if selection is None:return
    for kind in KINDS:
        existing={item['id'] for item in record[kind]}
        if any(item['id'] in existing and item['id'] not in selection[kind] for item in updates[kind]):
            raise ValueError('No se pueden reemplazar notas existentes que no se han cargado completas')
