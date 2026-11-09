"""Validated narrative memory. This module never resolves game mechanics."""
import time
import adventure_modules

MEMORY_SCHEMA={'type':'object','properties':{
    'summary':{'type':'string'},'location':{'type':'string'},'goal':{'type':'string'},
    'objectives':{'type':'array','items':{'type':'string'}},'preparation':{'type':'string'}},
    'required':['summary','location','goal','objectives','preparation'],'additionalProperties':False}
COMPACT_MEMORY_SCHEMA={'type':'object','properties':{'summary':{'type':'string'},'preparation':{'type':'string'}},
    'required':['summary','preparation'],'additionalProperties':False}


def text(value,limit,label):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:
        raise ValueError('Memoria de aventura inválida: '+label)
    return value.strip()


def validate_memory(value):
    if not isinstance(value,dict) or set(value)!=set(MEMORY_SCHEMA['required']):
        raise ValueError('Memoria de aventura incompleta o con campos no permitidos')
    result={key:text(value[key],limit,key) for key,limit in
            [('summary',6000),('location',200),('goal',500),('preparation',8000)]}
    objectives=value['objectives']
    if not isinstance(objectives,list) or len(objectives)>12:
        raise ValueError('Máximo doce objetivos narrativos')
    result['objectives']=[text(item,300,'objetivo') for item in objectives]
    if len(set(result['objectives']))!=len(result['objectives']):
        raise ValueError('Objetivos narrativos duplicados')
    return result


def memory_for_state(state,value):
    """Reconstruct authored facts locally; keep full historical memory compatible."""
    if isinstance(value,dict) and set(value)=={'summary','preparation'}:
        module=state.get('adventureModule')
        if not module:raise ValueError('La memoria breve necesita una escena preparada')
        public=adventure_modules.public_view(state)
        value={**value,'location':module['location'],'goal':module['goal'],
            'objectives':[item['text'] for item in public['objectives'] if not item['completed']]}
    return validate_memory(value)


def ready_characters(state):
    import board_scenes
    return [c for c in board_scenes.characters(state) if not c.get('enemy') and c.get('creation')
            and not c['creation'].get('manualOverride') and c.get('hp',0)>0
            and not c.get('conditions','').strip()]


def source_text(body):
    """Bound imported prose before inference; documents are untrusted private data."""
    if 'sourceText' not in body:return None
    if body.get('moduleId') or body.get('module') is not None:
        raise ValueError('Elige una sola fuente de aventura')
    value=text(body['sourceText'],12000,'texto aportado (máximo 12.000 caracteres)')
    if any(ord(c)<32 and c not in '\n\r\t' for c in value):
        raise ValueError('El documento debe contener texto legible, no datos binarios')
    return value


def validate_start(state,body,me):
    if not me['host']:raise PermissionError('Solo el anfitrión inicia la aventura compartida')
    if state.get('preparedOpening'):raise ValueError('Conserva la apertura original de esta campaña; continúa su investigación')
    if state.get('pfEncounter'):raise ValueError('La escena preparada usa su propio recorrido; no se mezcla con una investigación tranquila')
    if state.get('adventure'):raise ValueError('La aventura ya está iniciada; continúa en la conversación')
    if state['board']['active']:raise ValueError('Finaliza el combate antes de iniciar la aventura')
    if not ready_characters(state):
        raise ValueError('Crea primero un personaje con el asistente, sin edición manual ni condiciones pendientes')
    return text(body.get('premise',state['goal']),2000,'premisa')


def apply_memory(state,value,starting=False):
    """Apply only the allowlisted narrative fields, after complete validation."""
    memory=memory_for_state(state,value)
    if not starting and not state.get('adventure'):
        raise ValueError('Inicia la aventura antes de actualizar su memoria')
    if state['board']['active'] and memory['location']!=state['location']:
        raise ValueError('La memoria narrativa no puede trasladar un combate activo')
    revision=state.get('adventure',{}).get('revision',0)+1
    state['adventure']={'summary':memory['summary'],'revision':revision,'updatedAt':time.time(),
                        'source':'Memoria narrativa de IA; no certifica reglas ni consecuencias mecánicas'}
    state['directorMemory']=memory['preparation']
    state['location']=memory['location'];state['goal']=memory['goal'];state['objectives']=memory['objectives']
    if state.get('adventureModule'):
        # The authored module and confirmed discoveries outrank a narrative paraphrase.
        module=state['adventureModule'];public=adventure_modules.public_view(state)
        state['location']=module['location'];state['goal']=module['goal']
        state['objectives']=[item['text'] for item in public['objectives'] if not item['completed']]


def continuation_request(state,me):
    if not state.get('adventure'):raise ValueError('Inicia primero una aventura')
    if any(p.get('check') for p in state['pending']):raise ValueError('Resuelve primero las pruebas pendientes')
    last_director=max((i for i,m in enumerate(state['messages']) if m.get('kind')=='director' and not m.get('ooc')),default=-1)
    results=[m for i,m in enumerate(state['messages']) if i>last_director and m.get('check')]
    if not results:raise ValueError('No hay resultados nuevos que narrar')
    if not me['host']:
        owned={c['id'] for c in state['characters'] if c['owner']==me['id']}
        if not any(m['check'].get('character') in owned for m in results):
            raise PermissionError('Solo quien controla un personaje de estas pruebas puede continuar su resolución')
    return ('Narra las consecuencias ficticias de las pruebas ya resueltas por el motor desde tu última intervención. '
            'Lee sus resultados en el historial y respeta su éxito o fallo. No vuelvas a tirar, no elijas nuevas '
            'acciones de los jugadores ni apliques efectos mecánicos no implementados. Actualiza la memoria pública '
            'y privada con lo efectivamente descubierto; ofrece la siguiente situación abierta.')
