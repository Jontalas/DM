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
    if len(_canonical(state).encode('utf-8'))>MAX_BYTES:raise RulePackError('La campaña supera su límite de estado; conserva una copia antes de ampliar o archivar datos')


@lru_cache(maxsize=16)
def _compiled(campaign,document):
    # Campaign scope prevents reusing private compilation data across campaigns.
    return RulePack(document)


def runtime(state,campaign):
    record=state.get('package')
    if not isinstance(record,dict):raise RulePackError('Importa primero un paquete de reglas')
    _keys(record,('document','sha256','policy'))
    pack=_compiled(campaign,_canonical(record['document']))
    if pack.digest!=record['sha256']:raise RulePackError('El contenido del paquete no coincide con su huella guardada')
    if record['policy'] not in ('draft','provided-rules'):raise RulePackError('No existe verificación de fuentes para la política declarada')
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
    return {'ruleset':ID,'package':None,'authoring':None,'characters':[],'messages':[],
        'tone':str(config.get('tone',''))[:200],'limits':str(config.get('limits',''))[:2000],
        'goal':str(config.get('goal',''))[:2000]}


def _system(state,text,actor):
    state['messages'].append({'kind':'system','text':text,'actor':actor,'time':time.time()})


def execute_action(state,body,me):
    action={key:value for key,value in body.items() if key not in ('id','version')}
    if state.get('ruleset')!=ID:raise RulePackError('Esta campaña no usa el motor de paquetes')
    if len(state['messages'])>=MAX_MESSAGES:raise RulePackError('El registro alcanza su límite; conserva una copia antes de ampliar o archivar datos')
    kind=action.get('type');result=copy.deepcopy(state)
    if kind=='prepare_rule_pack':
        if not me['host']:raise PermissionError('Solo el anfitrión prepara reglas desde documentos')
        _keys(action,('type','request'))
        if state['characters']:raise RulePackError('Prepara otra campaña para nuevas reglas; la migración de fichas todavía no está disponible')
        from rule_pack_authoring import prepare_input,propose,MAX_RESPONSE
        prepared=prepare_input(action['request'])
        if state.get('authoring') and state['authoring']['sha256']==prepared['sha256']:raise RulePackError('Estos fragmentos y alcance ya tienen una preparación guardada; revísala sin repetir la llamada')
        # Reserve bounded space before a potentially billable provider call.
        result['authoring']={'request':prepared['request'],'sha256':prepared['sha256'],'report':'x'*(MAX_RESPONSE+12000)}
        _size(result)
        result['authoring']['report']=propose(prepared)
        _system(result,'Preparación de reglas guardada; requiere revisión y no ha sustituido el paquete de la campaña.',me['id'])
    elif kind=='install_prepared_rule_pack':
        if not me['host']:raise PermissionError('Solo el anfitrión instala la preparación')
        _keys(action,('type','preparation','policy'));record=state.get('authoring')
        if not record or record['sha256']!=action['preparation']:raise RulePackError('La preparación ha cambiado; revísala de nuevo')
        report=record['report']
        if report['status']!='candidate':raise RulePackError('La preparación contiene cuestiones sin resolver y no se puede ejecutar')
        return execute_action(state,{'type':'install_rule_pack','package':report['candidate'],'policy':action['policy']},me)
    elif kind=='install_rule_pack':
        if not me['host']:raise PermissionError('Solo el anfitrión instala reglas para esta campaña')
        if set(action)-{'type','package','policy'} or not {'type','package'}<=set(action):raise RulePackError('Importación de paquete inválida')
        policy=action.get('policy','draft')
        if policy not in ('draft','provided-rules'):raise RulePackError('No se puede declarar una verificación de fuentes desde la petición')
        pack=RulePack(action['package']);previous=state.get('package')
        if previous and previous['sha256']==pack.digest and previous['policy']==policy:raise RulePackError('Ese contenido y política ya están instalados; no se ha vuelto a guardar')
        if state['characters']:raise RulePackError('Hay fichas vinculadas al paquete; usa una campaña nueva hasta disponer de una migración verificada')
        result['package']={'document':pack.document(),'sha256':pack.digest,'policy':policy}
        _system(result,'Paquete importado: '+pack.document()['name']+' '+pack.version+'. Fidelidad al manual sin verificar.',me['id'])
    elif kind=='create_pack_sheet':
        _keys(action,('type','name'));pack=runtime(state,me['campaign'])
        if state['package']['policy']!='provided-rules':raise RulePackError('El paquete está en borrador; el anfitrión debe elegir expresamente usar sus definiciones aportadas')
        if len(state['characters'])>=100:raise RulePackError('Esta campaña admite hasta cien fichas')
        name=_text(action['name'],80)
        character={'id':secrets.token_hex(12),'name':name,'owner':me['id'],'sheet':pack.new_sheet(me['id'])}
        result['characters'].append(character);_system(result,'Ficha creada con valores iniciales del paquete: '+name,me['id'])
    elif kind=='run_pack_action':
        if set(action)-{'type','character','action','inputs','physical'} or not {'type','character','action'}<=set(action):raise RulePackError('Acción de paquete inválida')
        pack=runtime(state,me['campaign'])
        if state['package']['policy']!='provided-rules':raise RulePackError('El paquete todavía está en borrador')
        character=next((c for c in result['characters'] if c['id']==action['character']),None)
        if character is None:raise RulePackError('Ficha no disponible en esta campaña')
        sheet,trace=pack.execute(character['sheet'],action['action'],action.get('inputs',{}),me['id'],
            host=bool(me['host']),physical=action.get('physical'))
        character['sheet']=sheet
        result['messages'].append({'kind':'pack-action','character':character['id'],'actor':me['id'],
            'speaker':me['name'],'host':bool(me['host']),'time':time.time(),'action':action['action'],
            'inputs':copy.deepcopy(action.get('inputs',{})),'trace':trace})
    else:raise RulePackError('La operación no está definida por este motor; no se usarán reglas de otro sistema')
    _size(result);return result


def public_view(state,me):
    result=copy.deepcopy(state)
    if not me['host']:result.pop('authoring',None)
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
    if 'authoring' not in state:keys.remove('authoring') # Earlier experimental exports.
    _keys(state,keys)
    if state['ruleset']!=ID:raise RulePackError('Formato de campaña de paquetes incompatible')
    for key,limit in [('tone',200),('limits',2000),('goal',2000)]:
        if not isinstance(state[key],str) or len(state[key])>limit:raise RulePackError('Texto de campaña fuera de límites')
    if not isinstance(state['characters'],list) or len(state['characters'])>100:raise RulePackError('Lista de fichas inválida')
    if not isinstance(state['messages'],list) or len(state['messages'])>MAX_MESSAGES:raise RulePackError('Registro de campaña fuera de límites')
    if state.get('authoring') is not None:
        from rule_pack_authoring import validate_record
        validate_record(state['authoring'])
    if state['package'] is None:
        if state['characters']:raise RulePackError('Estado de fichas sin paquete')
        for event in state['messages']:
            _keys(event,('kind','text','actor','time'))
            if event['kind']!='system' or type(event['time']) not in (int,float) or not math.isfinite(event['time']):raise RulePackError('Registro sin paquete inválido')
            _text(event['text'],2000);_text(event['actor'],100)
        _size(state);return
    pack=runtime(state,campaign);sheets={};ids=set()
    if state['characters'] and state['package']['policy']!='provided-rules':raise RulePackError('Un paquete en borrador no admite fichas activas')
    for character in state['characters']:
        _keys(character,('id','name','owner','sheet'));identifier=_text(character['id'],200)
        if identifier in ids:raise RulePackError('Ficha duplicada')
        ids.add(identifier);_text(character['name'],80);_text(character['owner'],100)
        if not isinstance(character['sheet'],dict) or character['owner']!=character['sheet'].get('owner'):raise RulePackError('La ficha pertenece a otro propietario')
        pack.view(character['sheet']);sheets[identifier]=pack.new_sheet(character['owner'])
    for event in state['messages']:
        if not isinstance(event,dict):raise RulePackError('Registro de campaña inválido')
        if type(event.get('time')) not in (int,float) or not math.isfinite(event['time']):raise RulePackError('Fecha de registro inválida')
        _text(event.get('actor'),100)
        if event.get('kind')=='system':
            _keys(event,('kind','text','actor','time'));_text(event['text'],2000);continue
        _keys(event,('kind','character','actor','speaker','host','time','action','inputs','trace'))
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
        sheets[event['character']]=restored
    for character in state['characters']:
        if _canonical(character['sheet'])!=_canonical(sheets[character['id']]):raise RulePackError('Los valores actuales no coinciden con las acciones registradas')
    _size(state)


def import_campaign(incoming,me):
    if not me['host']:raise PermissionError('Solo el anfitrión recupera una campaña completa')
    result=copy.deepcopy(incoming);validate_restored(result,me['campaign'])
    for character in result['characters']:
        character['owner']=me['id'];character['sheet']['owner']=me['id']
    validate_restored(result,me['campaign']);return result
