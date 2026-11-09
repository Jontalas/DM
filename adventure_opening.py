"""An authored scene already has an introduction; do not infer it again."""
import hashlib
import re
import adventure_modules as modules
import campaign_world
from rule_pack_authoring import canonical

CONTRACT='authored-opening-1'
ACTION_CONTRACT='pf-authored-opening-1'
FORMAT='cronicas-authored-opening-1'


def prepared_reply(state):
    if state.get('preparedOpening'):raise ValueError('Conserva la apertura original de esta campaña')
    module=modules.validate_module(state.get('adventureModule'))
    result={'narration':module['description'],'proposals':[],
        'memory':{'summary':module['description'],'preparation':module['preparation']}}
    if campaign_world.enabled(state):result['worldUpdates']={'npcs':[],'places':[],'relationships':[]}
    return result


def receipt(state):
    module=modules.validate_module(state.get('adventureModule'))
    return {'format':FORMAT,'moduleSha256':hashlib.sha256(canonical(module).encode('utf-8')).hexdigest()}


def validate_restored(state):
    record=state.get('preparedOpening')
    markers=[m['preparedOpeningSha256'] for m in state.get('messages',[]) if 'preparedOpeningSha256' in m]
    if record is None:
        if markers:raise ValueError('Falta la procedencia del comienzo preparado')
        return
    if (not isinstance(record,dict) or set(record)!={'format','moduleSha256'} or record['format']!=FORMAT
        or not isinstance(record['moduleSha256'],str) or not re.fullmatch('[a-f0-9]{64}',record['moduleSha256'])
        or markers!=[record['moduleSha256']] or not state.get('adventure')):
        raise ValueError('La apertura preparada no corresponde a su registro')
    if state.get('adventureChapters'):module=state['adventureChapters']['completed'][0]['module']
    elif state.get('adventureRoute'):
        import adventure_routes
        module=adventure_routes.scene(state,state['adventureRoute']['start'])['module']
    else:module=state.get('adventureModule')
    expected=receipt({'adventureModule':module})
    if expected!=record:raise ValueError('Se ha alterado el original del comienzo preparado')
