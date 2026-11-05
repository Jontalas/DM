"""Canonical engine facts for rendering and a small opt-in director context."""
import copy
import hashlib
from rule_pack_runtime import RulePackError


def build(state,memory,pack):
    continuation=memory['continuation'];index=continuation['message'];event=state['messages'][index]
    data=pack.document();labels=data['fields'];action=data['actions'][event['action']]
    declarations=[message for message in state['messages'][:index] if message.get('kind')=='pack-talk'
        and message.get('mode')=='action' and message.get('character')==event['character']]
    intent=declarations[-1]['text'] if declarations else ''
    outputs={}
    for field,value in event['trace'].get('results',{}).items():
        if isinstance(value,str) and len(value)>500:
            outputs[field]={'label':labels[field]['label'],'textOmitted':True,'characters':len(value),'sha256':hashlib.sha256(value.encode()).hexdigest()}
        else:outputs[field]={'label':labels[field]['label'],'value':copy.deepcopy(value)}
    changes={}
    for batch in [event['trace']['changes'],*[trigger['changes'] for trigger in event['trace']['triggers']]]:
        for field,values in batch.items():
            if field not in changes:changes[field]={'label':labels[field]['label'],'before':copy.deepcopy(values['before'])}
            changes[field]['after']=copy.deepcopy(values['after'])
    proof=event.get('objectiveResolution')
    result={'action':event['action'],'actionLabel':action['label'],'character':event['character'],
        'declaredIntent':intent,'inputs':copy.deepcopy(event['inputs']),'outputs':outputs,'changes':changes,
        'rolls':[{'id':key,'total':roll['total'],'values':roll['values'][:20],'omittedValues':max(0,len(roll['values'])-20)}
            for key,roll in event['trace']['rolls'].items() if roll.get('rolled')],
        'objectiveLink':'none' if proof is None else 'completed' if proof['met'] else 'not-completed',
        'objectiveStates':[{'id':goal['id'],'title':goal['title'],'status':goal['status'],
            'completedByThisResult':bool(proof and proof['met'] and proof['objective']==goal['id'])}
            for goal in memory.get('objectives',[]) if goal['known']]}
    if proof is not None:result['objectiveResolution']=copy.deepcopy(proof)
    if 'discoveries' in memory:
        from adventure_discoveries import public_view
        result['discoveriesRevealed']=public_view(memory['discoveries']['catalog'],event.get('discoveryReveals',[]))
    if 'targetRef' in event:
        from rule_pack_actors import public_view
        reference=event['targetRef']
        actor=next((actor for actor in state.get('actors',[]) if actor['id']==reference['id'] and actor['npc']==reference['npc']),None)
        visible=public_view([actor],pack,memory.get('npcs',[])) if actor is not None else []
        if not visible:raise RulePackError('La continuación carece de un objetivo conocido confirmado')
        target=visible[0]
        evidence=next((record for record in state.get('targetResolutions',[]) if record['message']==index),None)
        if evidence is None:raise RulePackError('La continuación carece de evidencia privada de la resolución dirigida')
        published=set(evidence.get('sharedFields',[]))&set(actor['publicFields']);target_changes={}
        proof=evidence['trace']['target']
        for batch in [proof['changes'],*[trigger['changes'] for trigger in proof['triggers']]]:
            for field,values in batch.items():
                if field not in published:continue
                if field not in target_changes:target_changes[field]={'label':labels[field]['label'],'before':copy.deepcopy(values['before'])}
                target_changes[field]['after']=copy.deepcopy(values['after'])
        for values in target_changes.values():
            for key in ('before','after'):
                value=values[key]
                if isinstance(value,str) and len(value)>500:
                    values[key]={'textOmitted':True,'characters':len(value),'sha256':hashlib.sha256(value.encode()).hexdigest()}
        target['changes']=target_changes
        for field in target['fields'].values():
            value=field['value']
            if isinstance(value,str) and len(value)>500:
                field.pop('value');field.update(textOmitted=True,characters=len(value),sha256=hashlib.sha256(value.encode()).hexdigest())
        if 'targetContext' in action:
            character=next(character for character in state['characters'] if character['id']==event['character'])
            target['context']={'kind':'abstract-scene','sharedPerception':pack.shared_target_context(action['targetContext'],
                pack.view(character['sheet'])['fields'],pack.view(actor['sheet'])['fields'])}
        result['target']=target
    return result
