"""One campaign adapter for all rule-data packages, not one adapter per game.

No package is certified against a source by this structural importer. Execution
requires the host's explicit provided-rules policy until source review exists.
"""
import copy
from functools import lru_cache
import json
import math
import secrets
import time
from rule_pack_runtime import RulePack,RulePackError,FORMAT,CAPABILITIES,OPS

ID='rule-pack'
MAX_BYTES=750000
MAX_MESSAGES=5000


def _canonical(value):
    try:return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    except (TypeError,ValueError,RecursionError):raise RulePackError('Datos de campaña no serializables') from None


def _text(value,limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:raise RulePackError('Texto de campaña inválido')
    return value.strip()


def _keys(value,required):
    if not isinstance(value,dict) or set(value)!=set(required):raise RulePackError('Campos de campaña incompletos o no admitidos')


def _size(state):
    if len(state.get('messages',[]))>MAX_MESSAGES:raise RulePackError('El registro alcanza su límite; conserva una copia antes de ampliar o archivar datos')
    game={key:value for key,value in state.items() if key not in ('authoring','authoringWorkspace','adventureSource')}
    if len(_canonical(game).encode('utf-8'))>MAX_BYTES:raise RulePackError('La campaña supera su límite de estado; conserva una copia antes de ampliar o archivar datos')
    for field in ('authoring','authoringWorkspace'):
        if state.get(field) is not None and len(_canonical(state[field]).encode('utf-8'))>MAX_BYTES:raise RulePackError('Las preparaciones privadas superan su límite independiente')
    if state.get('adventureSource') is not None:
        from adventure_source import validate
        validate(state['adventureSource'])


@lru_cache(maxsize=16)
def _compiled(campaign,document):
    # Campaign scope prevents reusing private compilation data across campaigns.
    return RulePack(document)


def runtime(state,campaign):
    record=state.get('package')
    if not isinstance(record,dict):raise RulePackError('Importa primero un paquete de reglas')
    _keys(record,('document','sha256','policy','composition') if 'composition' in record else ('document','sha256','policy'))
    pack=_compiled(campaign,_canonical(record['document']))
    if pack.digest!=record['sha256']:raise RulePackError('El contenido del paquete no coincide con su huella guardada')
    if record['policy'] not in ('draft','provided-rules'):raise RulePackError('No existe verificación de fuentes para la política declarada')
    if 'composition' in record:
        from rule_pack_composition import validate_provenance
        validate_provenance(record['composition'],pack)
    return pack


def resources():
    return {'format':FORMAT,'engineVersion':1,'capabilities':sorted(CAPABILITIES),
        'operations':sorted(OPS),'maxPackageBytes':256000,'sourceVerification':'not-implemented'}


def inspect_document(document):
    return _description(RulePack(document))


def _description(pack):
    data=pack.document()
    return {'id':pack.id,'version':pack.version,'sha256':pack.digest,'name':data['name'],'edition':data['edition'],
        'license':data['license'],'sources':data['sources'],'coverage':data['coverage'],
        'fields':len(data['fields']),'actions':len(data['actions']),'tables':len(data['tables']),
        'structuralValidation':'passed','sourceVerification':'unverified',
        'executionPolicy':'Requires explicit use as provided rules; not certified against the manual'}


def initial_state(config):
    return {'ruleset':ID,'package':None,'authoring':None,'authoringWorkspace':None,'authoringWorkspaceRef':None,'adventureSource':None,'adventureSourceRef':None,'narrative':None,'characters':[],'messages':[],
        'tone':str(config.get('tone',''))[:200],'limits':str(config.get('limits',''))[:2000],
        'goal':str(config.get('goal',''))[:2000]}


def _system(state,text,actor):
    state['messages'].append({'kind':'system','text':text,'actor':actor,'time':time.time()})


def preparation_record(state,digest=None):
    if digest is not None and not isinstance(digest,str):raise RulePackError('Identificador de preparación inválido')
    workspace=state.get('authoringWorkspace')
    if workspace is not None:
        from rule_preparation_workspace import expand
        selected=digest if digest is not None else workspace['latest']
        if selected is None:return None
        return expand(workspace,selected)
    record=state.get('authoring')
    return copy.deepcopy(record) if record and (digest is None or digest==record['sha256']) else None


def execute_action(state,body,me,prepare_record=None,narrative_call=None,draw=None,source_loader=None):
    action={key:value for key,value in body.items() if key not in ('id','version')}
    if state.get('ruleset')!=ID:raise RulePackError('Esta campaña no usa el motor de paquetes')
    if len(state['messages'])>=MAX_MESSAGES:raise RulePackError('El registro alcanza su límite; conserva una copia antes de ampliar o archivar datos')
    kind=action.get('type');result=copy.deepcopy(state)
    import rule_pack_narrative as narrative
    if kind in narrative.ACTIONS:
        result=narrative.apply(state,action,me,runtime(state,me['campaign']),call=narrative_call,draw=draw,source_loader=source_loader)
        _size(result);return result
    if kind=='prepare_rule_pack':
        if not me['host']:raise PermissionError('Solo el anfitrión prepara reglas desde documentos')
        _keys(action,('type','request'))
        if state['characters']:raise RulePackError('Prepara otra campaña para nuevas reglas; la migración de fichas todavía no está disponible')
        from rule_pack_authoring import prepare_input,propose
        import rule_preparation_workspace as workspaces
        prepared=prepare_input(action['request'])
        workspace=state.get('authoringWorkspace')
        if workspace is None:workspace=workspaces.from_legacy(state.get('authoring'))
        if prepared['sha256'] in workspace['blocks']:raise RulePackError('Estos fragmentos y alcance ya tienen un bloque guardado; consúltalo sin repetir la llamada')
        # Reserve bounded space before a potentially billable provider call.
        result['authoring']=None;result['authoringWorkspace']=workspaces.reserve(workspace,prepared)
        _size(result)
        record=prepare_record(prepared) if prepare_record is not None else {'request':prepared['request'],'sha256':prepared['sha256'],'sourceScheme':prepared['sourceScheme'],'report':propose(prepared)}
        result['authoringWorkspace']=workspaces.add(workspace,record)
        _system(result,'Preparación de reglas guardada; requiere revisión y no ha sustituido el paquete de la campaña.',me['id'])
    elif kind=='install_prepared_rule_pack':
        if not me['host']:raise PermissionError('Solo el anfitrión instala la preparación')
        _keys(action,('type','preparation','policy'));record=preparation_record(state,action['preparation'])
        if not record:raise RulePackError('La preparación no está disponible; revísala de nuevo')
        report=record['report']
        if report['status']!='candidate':raise RulePackError('La preparación contiene cuestiones sin resolver y no se puede ejecutar')
        return execute_action(state,{'type':'install_rule_pack','package':report['candidate'],'policy':action['policy']},me)
    elif kind=='compose_rule_pack':
        if not me['host']:raise PermissionError('Solo el anfitrión combina reglas')
        _keys(action,('type','additional','versionTarget','baseSha256','expectedSha256','policy'))
        if state['characters']:raise RulePackError('Hay fichas vinculadas; la composición no migra partidas existentes')
        base=runtime(state,me['campaign'])
        if action['baseSha256']!=base.digest:raise RulePackError('El paquete de partida ha cambiado; revisa de nuevo la composición')
        if not isinstance(action['additional'],list) or not 1<=len(action['additional'])<=31:raise RulePackError('Selecciona entre uno y treinta y un bloques adicionales')
        if action['policy'] not in ('draft','provided-rules'):raise RulePackError('Política de uso de la composición inválida')
        from rule_pack_composition import compose
        combined=compose([base.document(),*action['additional']],action['versionTarget'])
        digest=combined['provenance']['packageSha256']
        if digest!=action['expectedSha256']:raise RulePackError('La combinación difiere de la revisión; no se ha instalado')
        result['package']={'document':combined['document'],'sha256':digest,'policy':action['policy'],'composition':combined['provenance']}
        _system(result,'Reglas combinadas en versión '+action['versionTarget']+'. Fuentes sin verificar; no se han migrado fichas.',me['id'])
    elif kind=='install_rule_pack':
        if not me['host']:raise PermissionError('Solo el anfitrión instala reglas para esta campaña')
        if set(action)-{'type','package','policy'} or not {'type','package'}<=set(action):raise RulePackError('Importación de paquete inválida')
        policy=action.get('policy','draft')
        if policy not in ('draft','provided-rules'):raise RulePackError('No se puede declarar una verificación de fuentes desde la petición')
        pack=RulePack(action['package']);previous=state.get('package')
        if previous and previous['sha256']==pack.digest and previous['policy']==policy:raise RulePackError('Ese contenido y política ya están instalados; no se ha vuelto a guardar')
        if state['characters']:raise RulePackError('Hay fichas vinculadas al paquete; usa una campaña nueva hasta disponer de una migración verificada')
        result['package']={'document':pack.document(),'sha256':pack.digest,'policy':policy}
        if previous and previous['sha256']==pack.digest and 'composition' in previous:
            result['package']['composition']=copy.deepcopy(previous['composition'])
        _system(result,'Paquete importado: '+pack.document()['name']+' '+pack.version+'. Fidelidad al manual sin verificar.',me['id'])
    elif kind=='create_pack_sheet':
        if set(action)-{'type','name','inputs','physical'} or not {'type','name'}<=set(action):raise RulePackError('Datos de creación no admitidos')
        pack=runtime(state,me['campaign'])
        if state['package']['policy']!='provided-rules':raise RulePackError('El paquete está en borrador; el anfitrión debe elegir expresamente usar sus definiciones aportadas')
        if len(state['characters'])>=100:raise RulePackError('Esta campaña admite hasta cien fichas')
        if state.get('narrative') is not None and len(state['characters'])>=8:raise RulePackError('El director experimental admite como máximo ocho fichas')
        name=_text(action['name'],80)
        sheet,trace=pack.create_character(me['id'],action.get('inputs',{}),physical=action.get('physical'),draw=draw)
        character={'id':secrets.token_hex(12),'name':name,'owner':me['id'],'sheet':sheet}
        if trace is not None:character['creation']={'inputs':copy.deepcopy(action.get('inputs',{})),'trace':trace}
        result['characters'].append(character);_system(result,'Ficha creada con valores iniciales del paquete: '+name,me['id'])
    elif kind=='run_pack_action':
        if state.get('narrative') is not None:raise RulePackError('Declara la acción en la aventura para conectarla con la ficción y el estado')
        if set(action)-{'type','character','action','inputs','physical'} or not {'type','character','action'}<=set(action):raise RulePackError('Acción de paquete inválida')
        pack=runtime(state,me['campaign'])
        if state['package']['policy']!='provided-rules':raise RulePackError('El paquete todavía está en borrador')
        character=next((c for c in result['characters'] if c['id']==action['character']),None)
        if character is None:raise RulePackError('Ficha no disponible en esta campaña')
        sheet,trace=pack.execute(character['sheet'],action['action'],action.get('inputs',{}),me['id'],
            host=bool(me['host']),physical=action.get('physical'),draw=draw)
        character['sheet']=sheet
        result['messages'].append({'kind':'pack-action','character':character['id'],'actor':me['id'],
            'speaker':me['name'],'host':bool(me['host']),'time':time.time(),'action':action['action'],
            'inputs':copy.deepcopy(action.get('inputs',{})),'trace':trace})
    else:raise RulePackError('La operación no está definida por este motor; no se usarán reglas de otro sistema')
    _size(result);return result


def public_view(state,me):
    result=copy.deepcopy(state)
    source=result.pop('adventureSource',None);source_ref=result.pop('adventureSourceRef',None)
    if me['host'] and (source is not None or source_ref is not None):
        import adventure_source
        meta=adventure_source.reference(source) if source is not None else adventure_source.validate_ref(source_ref)
        result['adventureSourceView']={'title':meta['title'],'characters':meta['characters'],'sourceVerification':'unverified'}
    if 'narrative' in result:
        import rule_pack_narrative as narrative
        result['narrativeView']=narrative.public_view(result.pop('narrative'))
    if not me['host']:result.pop('authoring',None);result.pop('authoringWorkspace',None);result.pop('authoringWorkspaceRef',None)
    if state.get('package'):
        pack=runtime(state,me['campaign'])
        result['packageView']=_description(pack)|{'policy':state['package']['policy']}
        for character in result['characters']:
            character['view']=pack.view(character['sheet'])
    return result


def _comparable_trace(trace):
    result=copy.deepcopy(trace)
    for record in result['rolls'].values():
        origin=record.pop('origin',None)
        if record.get('rolled') and origin not in ('server','physical'):raise RulePackError('Origen de dado inválido en el registro')
        if not record.get('rolled') and origin is not None:raise RulePackError('Una tirada omitida no tiene origen de dados')
    return _canonical(result)


def validate_restored(state,campaign='import-validation'):
    keys=set(initial_state({}))
    for optional in ('authoring','authoringWorkspace','authoringWorkspaceRef','narrative','adventureSource','adventureSourceRef'):
        if optional not in state:keys.remove(optional) # Earlier experimental exports.
    _keys(state,keys)
    if state['ruleset']!=ID:raise RulePackError('Formato de campaña de paquetes incompatible')
    if state.get('authoringWorkspaceRef') is not None:raise RulePackError('La copia debe incluir las fuentes completas; usa Guardar copia en la campaña original')
    if state.get('adventureSourceRef') is not None:raise RulePackError('La copia debe incluir la fuente completa de aventura; guarda una copia desde la campaña original')
    if state.get('adventureSource') is not None:
        import adventure_source
        adventure_source.validate(state['adventureSource'])
    for key,limit in [('tone',200),('limits',2000),('goal',2000)]:
        if not isinstance(state[key],str) or len(state[key])>limit:raise RulePackError('Texto de campaña fuera de límites')
    if not isinstance(state['characters'],list) or len(state['characters'])>100:raise RulePackError('Lista de fichas inválida')
    if not isinstance(state['messages'],list) or len(state['messages'])>MAX_MESSAGES:raise RulePackError('Registro de campaña fuera de límites')
    _size(state)
    if state.get('authoringWorkspace') is not None:
        if state.get('authoring') is not None:raise RulePackError('La copia contiene dos representaciones de preparaciones; no se mezclan silenciosamente')
        from rule_preparation_workspace import validate
        validate(state['authoringWorkspace'])
    if state.get('authoring') is not None:
        from rule_pack_authoring import validate_record
        validate_record(state['authoring'])
    if state['package'] is None:
        if state.get('narrative') is not None:raise RulePackError('Aventura sin paquete de reglas')
        if state['characters']:raise RulePackError('Estado de fichas sin paquete')
        for event in state['messages']:
            _keys(event,('kind','text','actor','time'))
            if event['kind']!='system' or type(event['time']) not in (int,float) or not math.isfinite(event['time']):raise RulePackError('Registro sin paquete inválido')
            _text(event['text'],2000);_text(event['actor'],100)
        _size(state);return
    pack=runtime(state,campaign);sheets={};ids=set()
    if state['characters'] and state['package']['policy']!='provided-rules':raise RulePackError('Un paquete en borrador no admite fichas activas')
    for character in state['characters']:
        _keys(character,('id','name','owner','sheet','creation') if pack.creation is not None else ('id','name','owner','sheet'));identifier=_text(character['id'],200)
        if identifier in ids:raise RulePackError('Ficha duplicada')
        ids.add(identifier);_text(character['name'],80);_text(character['owner'],100)
        if not isinstance(character['sheet'],dict) or character['owner']!=character['sheet'].get('owner'):raise RulePackError('La ficha pertenece a otro propietario')
        pack.view(character['sheet'])
        if pack.creation is not None:
            creation=character['creation'];_keys(creation,('inputs','trace'))
            trace=creation['trace'];_keys(trace,('action','sources','rolls','changes','triggers'))
            if not isinstance(trace['rolls'],dict) or any(not isinstance(v,dict) for v in trace['rolls'].values()):raise RulePackError('Dados de creación inválidos')
            physical={key:value.get('values') for key,value in trace['rolls'].items() if value.get('rolled')}
            sheet,expected=pack.create_character(character['owner'],creation['inputs'],physical=physical,
                draw=lambda sides:(_ for _ in ()).throw(RulePackError('Faltan dados de creación; no se ha vuelto a tirar')))
            if _comparable_trace(trace)!=_comparable_trace(expected):raise RulePackError('La creación no coincide con las reglas y dados guardados')
            sheets[identifier]=sheet
        else:sheets[identifier]=pack.new_sheet(character['owner'])
    for event in state['messages']:
        if not isinstance(event,dict):raise RulePackError('Registro de campaña inválido')
        if type(event.get('time')) not in (int,float) or not math.isfinite(event['time']):raise RulePackError('Fecha de registro inválida')
        _text(event.get('actor'),100)
        if event.get('kind')=='system':
            _keys(event,('kind','text','actor','time'));_text(event['text'],2000);continue
        if event.get('kind') in ('pack-talk','pack-director'):
            import rule_pack_narrative as narrative
            narrative.validate_event(event,ids);continue
        event_keys=('kind','character','actor','speaker','host','time','action','inputs','trace')
        _keys(event,(*event_keys,'objectiveResolution') if 'objectiveResolution' in event else event_keys)
        if event['kind']!='pack-action' or not isinstance(event['character'],str) or event['character'] not in sheets or type(event['host'])!=bool:raise RulePackError('Acción registrada inválida')
        _text(event['speaker'],120)
        trace=event['trace']
        _keys(trace,('action','sources','rolls','changes','triggers'))
        if not isinstance(trace['rolls'],dict) or any(not isinstance(v,dict) for v in trace['rolls'].values()):raise RulePackError('Dados registrados inválidos')
        physical={key:value.get('values') for key,value in trace['rolls'].items() if value.get('rolled')}
        previous=sheets[event['character']]
        # Verify mathematics, not historic identity authenticity of an external file.
        restored,expected=pack.execute(previous,event['action'],event['inputs'],previous['owner'],host=True,
            physical=physical,draw=lambda sides:(_ for _ in ()).throw(RulePackError('Faltan dados en el registro; no se ha vuelto a tirar')))
        if _comparable_trace(trace)!=_comparable_trace(expected):raise RulePackError('La resolución no coincide con las reglas y dados guardados')
        if 'objectiveResolution' in event:
            from rule_pack_objectives import validate_proof
            validate_proof(event['objectiveResolution'],event,restored,pack.document())
        sheets[event['character']]=restored
    for character in state['characters']:
        if _canonical(character['sheet'])!=_canonical(sheets[character['id']]):raise RulePackError('Los valores actuales no coinciden con las acciones registradas')
    import rule_pack_narrative as narrative
    narrative.validate(state,pack)
    _size(state)


def import_campaign(incoming,me):
    if not me['host']:raise PermissionError('Solo el anfitrión recupera una campaña completa')
    result=copy.deepcopy(incoming);validate_restored(result,me['campaign'])
    for character in result['characters']:
        character['owner']=me['id'];character['sheet']['owner']=me['id']
    validate_restored(result,me['campaign']);return result
