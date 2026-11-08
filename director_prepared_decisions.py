"""Existing prepared, deterministic decisions selected from a player declaration."""


def available(state):
    record=state.get('pfEncounter')
    if not record or state.get('mode','solo')!='solo' or state.get('ruleset','pathfinder-1e')!='pathfinder-1e':return None
    actor=next((c for c in state['characters'] if c['id']==record['character']),None)
    if not actor:return None
    import pf_ceasefire
    import pf_night_rest
    import pf_scene_transition
    actions=[]
    if pf_ceasefire.limitation(state) is None:
        actions.append({'id':'accept-truce','label':'Aceptar la tregua ofrecida; conservar heridas y permitir el paso'})
    night=pf_night_rest.public_view(state)
    if night and not night['completed'] and night['reason'] is None:
        prepared=night.get('armorPlan')=='remove-and-reequip'
        actions.append({'id':'sleep-after-removing-armor' if prepared else 'sleep-in-light-armor',
            'label':'Quitarse la cota, dormir8h sin ella y volver a equiparla normalmente;5min adicionales' if prepared
                else 'Elegir dormir8h con la armadura ligera puesta'})
    if pf_scene_transition.limitation(state) is None:
        actions.append({'id':'investigate-courtyard','label':'Comenzar a investigar el registro del patio, sin salir de él'})
    return {'character':actor['id'],'actions':actions} if actions else None


def declaration_available(state):
    if not state.get('messages') or state['messages'][-1].get('kind')!='action':return None
    return available(state)


def apply(state,item,body,me):
    if not isinstance(item,dict) or set(item)!={'action'} or not isinstance(item['action'],str):
        raise ValueError('Elige una única decisión preparada disponible')
    if body.get('type')!='talk' or body.get('kind')!='action':raise ValueError('La decisión requiere una declaración de acción')
    choices=declaration_available(state)
    if not choices or item['action'] not in {a['id'] for a in choices['actions']}:raise ValueError('La decisión preparada ya no está disponible')
    actor=next(c for c in state['characters'] if c['id']==choices['character'])
    if actor['owner']!=me['id'] or body.get('character') not in (None,actor['id']):raise PermissionError('Solo el propietario decide por su personaje')
    actions={'accept-truce':{'type':'accept_pf_ceasefire'},'sleep-in-light-armor':{'type':'rest_pf_night'},
        'sleep-after-removing-armor':{'type':'rest_pf_night','armorPlan':'remove-and-reequip'},
        'investigate-courtyard':{'type':'continue_pf_encounter'}}
    from engine import apply_action
    apply_action(state,actions[item['action']],me)
