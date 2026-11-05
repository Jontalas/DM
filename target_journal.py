"""Private chronological replay for two-sheet campaign resolutions.

The caller supplies player sheets already replayed from validated creation
records. This module replays all subsequent mechanical messages and verifies
both final state maps, never substituting a new roll or interpreting prose.
"""
import copy
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError
import actor_references
import rule_pack_actors as actors

MAX_RECORDS=128
MAX_BYTES=256000


def public_continuation(state):
    continuation=(state.get('narrative') or {}).get('continuation')
    return continuation is not None and any(record.get('message')==continuation['message']
        and record.get('continuationScope')=='public' for record in state.get('targetResolutions',[]))


def _no_draw(sides):raise RulePackError('Faltan dados confirmados; no se ha vuelto a tirar')


def _trace(trace):
    from rule_pack_campaign import _comparable_trace
    if not isinstance(trace,dict) or not isinstance(trace.get('rolls'),dict) or any(not isinstance(v,dict) for v in trace['rolls'].values()):
        raise RulePackError('Traza mecánica inválida')
    return _comparable_trace(trace)


def public_roll_shape(action,shared_fields):
    """Initial policy: public dice must not encode unshared target statistics."""
    def check(node):
        if isinstance(node,dict):
            path=node.get('ref')
            if isinstance(path,list) and path[0]=='target' and path[1] not in shared_fields:
                raise RulePackError('La forma pública de la tirada depende de un dato privado; esta visibilidad aún no está soportada')
            for value in node.values():check(value)
        elif isinstance(node,list):
            for value in node:check(value)
    for roll in action['rolls']:
        for key in ('count','sides','when'):check(roll.get(key))


def replay(state,pack,initial_players):
    document=pack.document()
    messages=state['messages'];records=state.get('targetResolutions',[])
    if not isinstance(records,list) or len(records)>MAX_RECORDS or len(canonical(records).encode('utf-8'))>MAX_BYTES:
        raise RulePackError('Registro privado de resoluciones fuera de límites')
    private={};last=-1
    for record in records:
        if not isinstance(record,dict) or not {'message','binding','inputs','trace'}<=set(record) or set(record)-{'message','binding','inputs','trace','sharedFields','continuationScope'}:raise RulePackError('Evidencia privada incompleta')
        if 'continuationScope' in record and record['continuationScope']!='public':raise RulePackError('Ámbito de continuación inválido')
        if 'sharedFields' in record:
            fields=record['sharedFields']
            if not isinstance(fields,list) or len(fields)>16 or any(not isinstance(field,str) or field not in document['fields'] for field in fields) or len(set(fields))!=len(fields):
                raise RulePackError('Publicación histórica de campos inválida')
        position=record['message']
        if type(position)!=int or not last<position<len(messages) or messages[position].get('kind')!='pack-action':
            raise RulePackError('Orden o referencia de resolución privada inválidos')
        private[position]=record;last=position
    players=copy.deepcopy(initial_players)
    if set(players)!={c['id'] for c in state['characters']}:raise RulePackError('Fichas iniciales ajenas al registro')
    for sheet in players.values():pack.view(sheet)
    registry=state.get('actors',[]);npcs=(state.get('narrative') or {}).get('npcs',[])
    if not isinstance(registry,list) or len(registry)>actors.MAX_ACTORS or len(canonical(registry).encode('utf-8'))>actors.MAX_BYTES:
        raise RulePackError('Registro de actores fuera de límites')
    npc_sheets={};references=set();by_id={}
    for actor in registry:
        initial=actors.initial(actor,pack,npcs);identifier=initial['id']
        if identifier in npc_sheets or identifier in players or initial['npc'] in references:raise RulePackError('Actor privado duplicado o incompatible')
        if 'introducedAt' in initial and initial['introducedAt']>len(messages):raise RulePackError('Actor preparado después del registro')
        npc_sheets[identifier]=initial['sheet'];by_id[identifier]=actor;references.add(initial['npc'])
    for position,event in enumerate(messages):
        if event.get('kind')!='pack-action':continue
        identifier=event.get('character')
        if not isinstance(identifier,str) or identifier not in players:raise RulePackError('Acción sin ficha del jugador')
        before=players[identifier];record=private.get(position)
        if record is None:
            if 'targetRef' in event:raise RulePackError('Referencia pública sin evidencia privada')
            _trace(event.get('trace'));physical={k:r.get('values') for k,r in event['trace']['rolls'].items() if r.get('rolled')}
            restored,expected=pack.execute(before,event['action'],event['inputs'],before['owner'],host=True,physical=physical,draw=_no_draw)
        else:
            binding=record['binding']
            if not isinstance(binding,dict) or binding.get('character')!=identifier or not isinstance(binding.get('target'),str):raise RulePackError('Evidencia ligada a otra ficha')
            target=by_id.get(binding['target'])
            if target is None or 'introducedAt' not in target or target['introducedAt']>position:
                raise RulePackError('La resolución precede a la preparación del actor objetivo')
            if event.get('targetRef')!={'id':binding['target'],'npc':binding.get('npc')} or canonical(event['inputs'])!=canonical(record['inputs']):
                raise RulePackError('El mensaje público y su evidencia privada difieren')
            snapshot={**state,'characters':[{**c,'sheet':players[c['id']]} for c in state['characters']],
                'actors':[{**a,'sheet':npc_sheets[a['id']]} for a in registry]}
            try:selected=actor_references.validate(binding,snapshot,{'id':before['owner']},pack)
            except PermissionError:raise RulePackError('Propietario incompatible con la referencia guardada') from None
            public_roll_shape(document['actions'][event['action']],record.get('sharedFields',target['publicFields']))
            _trace(record['trace']);physical={k:r.get('values') for k,r in record['trace']['rolls'].items() if r.get('rolled')}
            restored,other,full=pack.execute_targeted(before,selected,event['action'],record['inputs'],before['owner'],host=True,physical=physical,draw=_no_draw)
            if _trace(full)!=_trace(record['trace']):raise RulePackError('La resolución privada no coincide con las dos fichas y los dados')
            npc_sheets[binding['target']]=other;expected=copy.deepcopy(full);expected.pop('target')
        if _trace(expected)!=_trace(event['trace']):raise RulePackError('La traza pública difiere del resultado confirmado')
        if 'objectiveResolution' in event:
            from rule_pack_objectives import validate_proof
            validate_proof(event['objectiveResolution'],event,restored,document)
        players[identifier]=restored
    for character in state['characters']:
        if canonical(character['sheet'])!=canonical(players[character['id']]):raise RulePackError('La ficha del jugador difiere del registro mecánico')
    for actor in registry:
        if canonical(actor['sheet'])!=canonical(npc_sheets[actor['id']]):raise RulePackError('La ficha del actor difiere del registro privado')
    return {'players':players,'actors':npc_sheets}
