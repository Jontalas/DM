"""Canonical engine facts for rendering and a small opt-in director context."""
import copy
import hashlib


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
    return result
