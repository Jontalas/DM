"""Deterministic composition of reviewed packages for the same game/edition.

Inputs are complete, independently compilable blocks. Partial definitions and
state migrations are not supported here. Nothing is installed or persisted.
"""
import copy
import json
import re
from rule_pack_runtime import RulePack,RulePackError


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def compose(documents,version):
    if not isinstance(documents,list) or not 2<=len(documents)<=32:raise RulePackError('Combina entre dos y treinta y dos bloques de reglas')
    if not isinstance(version,str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version):raise RulePackError('Indica una nueva versión mayor.menor.revisión')
    packs=[RulePack(raw) for raw in documents]
    if len({pack.digest for pack in packs})!=len(packs):raise RulePackError('Hay bloques de contenido repetido; no se ha creado otra versión')
    target=tuple(map(int,version.split('.')))
    if any(target<=tuple(map(int,pack.version.split('.'))) for pack in packs):raise RulePackError('La composición necesita una versión posterior a todos sus bloques')
    # Input order cannot decide which rule or source wins.
    packs.sort(key=lambda pack:pack.digest)
    result=packs[0].document();result['version']=version
    sources={};groups={group:{} for group in ('fields','tables','actions','triggers')}
    coverage={'implemented':set(),'pending':set()};capabilities=set()
    for pack in packs:
        data=pack.document()
        for key in ('id','name','edition','license','engineVersion','format'):
            if _canonical(data[key])!=_canonical(result[key]):raise RulePackError('Los bloques difieren en '+key+'; no se mezclan juegos, ediciones ni atribuciones automáticamente')
        for source in data['sources']:
            identifier=source['id']
            if identifier in sources and _canonical(sources[identifier])!=_canonical(source):raise RulePackError('Una referencia de fuente tiene definiciones incompatibles: '+identifier)
            sources[identifier]=copy.deepcopy(source)
        for group,entries in groups.items():
            for identifier,definition in data[group].items():
                if identifier not in entries:entries[identifier]=copy.deepcopy(definition);continue
                existing=entries[identifier]
                old={key:value for key,value in existing.items() if key!='sources'}
                new={key:value for key,value in definition.items() if key!='sources'}
                if _canonical(old)!=_canonical(new):raise RulePackError('Definiciones incompatibles en '+group+'.'+identifier+'; se necesita una resolución explícita')
                existing['sources']=sorted(set(existing['sources'])|set(definition['sources']))
        capabilities.update(data['requires'])
        for key in coverage:coverage[key].update(data['coverage'][key])
    result.update({group:{key:entries[key] for key in sorted(entries)} for group,entries in groups.items()})
    for entries in groups.values():
        for definition in entries.values():definition['sources']=sorted(set(definition['sources']))
    result['sources']=[sources[key] for key in sorted(sources)]
    result['requires']=sorted(capabilities)
    # Pending coverage is retained: adding a block does not prove it resolved a gap.
    result['coverage']={key:sorted(values) for key,values in coverage.items()}
    compiled=RulePack(result)
    return {'document':compiled.document(),'provenance':{'format':'cronicas-rule-composition-1',
        'packageSha256':compiled.digest,'version':version,
        'inputs':[{'id':pack.id,'version':pack.version,'sha256':pack.digest} for pack in packs]},
        'sourceVerification':'unverified','stateMigration':'not-performed'}
