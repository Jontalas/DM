"""Two owners choose a shared next goal; no provider, persistence or dice."""
import copy
import hashlib
import re
import adventure
from rule_pack_authoring import canonical

FORMAT='cronicas-chapter-goal-1'
FIELD='chapterGoalProposal'
PROPOSE='propose_adventure_goal'
FIELDS={'format','author','premise','bindingSha256','id'}


def _hash(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def binding(state):
    # Chat and private notes do not change the consented game situation.
    return _hash({k:v for k,v in state.items() if k not in (FIELD,'messages','private') and not k.endswith('View')})


def _proposal_id(value):return _hash({k:v for k,v in value.items() if k!='id'})


def validate_shape(value):
    if (not isinstance(value,dict) or set(value)!=FIELDS or value.get('format')!=FORMAT
        or not isinstance(value.get('author'),str) or not 1<=len(value['author'])<=200
        or not isinstance(value.get('bindingSha256'),str) or not re.fullmatch('[a-f0-9]{64}',value['bindingSha256'])
        or not isinstance(value.get('id'),str) or value['id']!=_proposal_id(value)):
        raise ValueError('La propuesta de objetivo necesita revisarse')
    if adventure.text(value['premise'],2000,'objetivo del grupo')!=value['premise']:
        raise ValueError('La propuesta debe conservar el objetivo original')
    return copy.deepcopy(value)


def _require_owner(state,me):
    if not any(not c.get('enemy') and c.get('owner')==me['id'] for c in state.get('characters',[])):
        raise PermissionError('Solo los propietarios eligen el próximo objetivo de sus personajes')


def propose(state,body,me):
    if body.get('type')!=PROPOSE or set(body)-{'type','id','version','premise'}:
        raise ValueError('Propón un objetivo sin decidir por otros jugadores')
    _require_owner(state,me)
    import adventure_chapters as chapters
    reason=chapters.group_limitation(state,me)
    if reason:raise ValueError(reason)
    proposal={'format':FORMAT,'author':me['id'],'premise':adventure.text(body.get('premise'),2000,'objetivo del grupo'),
              'bindingSha256':binding(state)}
    proposal['id']=_proposal_id(proposal)
    result=copy.deepcopy(state);result[FIELD]=proposal
    return result


def accept(state,body,me):
    _require_owner(state,me)
    import adventure_chapters as chapters
    reason=chapters.group_limitation(state,me)
    if reason:raise ValueError(reason)
    proposal=validate_shape(state.get(FIELD))
    if proposal['author']==me['id']:raise PermissionError('Espera a que el otro propietario elija si continúa con este objetivo')
    owners={c['owner'] for c in state['characters']}
    if proposal['author'] not in owners:raise ValueError('El propietario de la propuesta ya no está en este grupo')
    if proposal['bindingSha256']!=binding(state):raise ValueError('La situación ha cambiado; proponed de nuevo el objetivo antes de continuar')
    if body.get('proposalId')!=proposal['id'] or body.get('premise')!=proposal['premise']:
        raise ValueError('La propuesta ha cambiado; revisa el objetivo antes de aceptarlo')
    return {'premise':proposal['premise'],'owners':sorted(owners)}


def public_view(state,me):
    import adventure_chapters as chapters
    reason=chapters.group_limitation(state,me)
    result={'kind':'group','reason':reason,'canPropose':reason is None,'proposal':None}
    if FIELD not in state:return result
    try:proposal=validate_shape(state[FIELD])
    except (ValueError,TypeError,KeyError):
        result['proposalReason']='La propuesta necesita revisarse. Un propietario puede plantear otra.'
        return result
    author=next((c for c in state['characters'] if c.get('owner')==proposal['author']),None)
    changed=proposal['bindingSha256']!=binding(state)
    proposal_reason=reason or ('La situación ha cambiado. Propón de nuevo el objetivo.' if changed else '')
    result['proposal']={'id':proposal['id'],'premise':proposal['premise'],'author':proposal['author'],
        'authorName':author['name'] if author else 'Otro jugador',
        'canAccept':not proposal_reason and proposal['author']!=me['id'],'reason':proposal_reason}
    return result
