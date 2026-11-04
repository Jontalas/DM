"""Experimental persisted creation drafts, based on Cairn SRD v1.0, Yochai Gal.

CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/
Source: https://cairnrpg.com/first-edition/cairn-srd/#character-creation
Changes: staged deterministic validation and immutable player choices.
Not registered or exposed as playable until the full adapter is integrated.
"""
import copy
import secrets
from systems import cairn_1e as rules,cairn_inventory as inventory

GEAR_TABLES=('armor','helmets--shields','weapons','expeditionary-gear','tools','trinkets')
BONUS_TABLE='bonus-item-roll-on-table-indicated'
FORMAT='cairn-creation-1'


def _draw(draw,sides,count=1):
    values=[draw(sides) for _ in range(count)]
    rules._dice(values,count,sides)
    return values


def begin(owner,name_table,draw=None):
    """Only call inside the server action transaction, after deduplication/permissions."""
    if not isinstance(owner,str) or not owner or len(owner)>100:raise ValueError('Propietario de creación inválido')
    if name_table not in ('female-names','male-names'):raise ValueError('Elige una tabla de nombres de Cairn')
    draw=draw or (lambda sides:secrets.randbelow(sides)+1)
    core={key:_draw(draw,6,3) for key in rules.ABILITIES}
    core.update(HP=_draw(draw,6),gold=_draw(draw,6,3),age=_draw(draw,20,2))
    identity={'name':_draw(draw,20)[0],'surname':_draw(draw,20)[0],
        'background':_draw(draw,20)[0],'traits':{key:_draw(draw,10)[0] for key in rules.TRAITS}}
    draft={'format':FORMAT,'draftId':secrets.token_hex(12),'owner':owner,'nameTable':name_table,'core':core,'identity':identity,
        'gear':{key:_draw(draw,20)[0] for key in GEAR_TABLES},'bonusRoll':_draw(draw,20)[0],'bonus':None}
    options=bonus_options(draft)
    if len(options)==1:
        table=options[0];draft['bonus']={'table':table,'raw':_draw(draw,100 if table=='spellbooks-d100' else 20)[0]}
    return draft


def bonus_options(draft):
    result=rules.table_result(BONUS_TABLE,draft['bonusRoll'])
    return {'Tool or Trinket':['tools','trinkets'],'Expeditionary Gear':['expeditionary-gear'],
        'Armor or Weapon':['armor','weapons'],'Spellbook':['spellbooks-d100']}[result]


def validate(draft):
    required={'format','owner','nameTable','core','identity','gear','bonusRoll','bonus'}
    if (not isinstance(draft,dict) or not required<=set(draft) or set(draft)-required-{'draftId'}
        or draft['format']!=FORMAT):raise ValueError('Borrador de Cairn inválido')
    if 'draftId' in draft and (not isinstance(draft['draftId'],str) or not draft['draftId'] or len(draft['draftId'])>100):raise ValueError('Identidad del borrador inválida')
    if not isinstance(draft['owner'],str) or not draft['owner'] or len(draft['owner'])>100:raise ValueError('Propietario de creación inválido')
    rules.core_from_rolls(draft['core'])
    identity=draft['identity']
    if not isinstance(identity,dict) or set(identity)!={'name','surname','background','traits'}:raise ValueError('Identidad de Cairn incompleta')
    rules.identity_from_rolls(draft['nameTable'],identity['name'],identity['surname'],identity['background'],identity['traits'])
    if not isinstance(draft['gear'],dict) or set(draft['gear'])!=set(GEAR_TABLES):raise ValueError('Tiradas de equipo incompletas')
    for table,raw in draft['gear'].items():rules.table_result(table,raw)
    options=bonus_options(draft);bonus=draft['bonus']
    if bonus is None:
        if len(options)==1:raise ValueError('Falta el resultado automático del objeto adicional')
    elif (not isinstance(bonus,dict) or set(bonus)!={'table','raw'} or bonus['table'] not in options):
        raise ValueError('La tabla adicional no corresponde al resultado original')
    else:rules.table_result(bonus['table'],bonus['raw'])
    return copy.deepcopy(draft)


def choose_bonus(draft,table,actor,draw=None):
    validated=validate(draft)
    if validated['owner']!=actor:raise PermissionError('No controlas este borrador de personaje')
    if validated['bonus'] is not None:raise ValueError('El objeto adicional ya se ha tirado; no se vuelve a tirar al revisar')
    if not isinstance(table,str) or table not in bonus_options(validated):raise ValueError('Tabla adicional no disponible')
    draw=draw or (lambda sides:secrets.randbelow(sides)+1)
    validated['bonus']={'table':table,'raw':_draw(draw,100 if table=='spellbooks-d100' else 20)[0]}
    return validated


def _group(identifier,table,raw):
    label=rules.table_result(table,raw)
    if table=='spellbooks-d100':options=['Spellbook: '+label]
    elif label=='None':options=[]
    elif table=='weapons':options=label.split(', ')
    elif table=='helmets--shields':options=label.split(' & ')
    else:options=[label]
    return {'id':identifier,'table':table,'raw':raw,'options':options,
        'chooseOne':table=='weapons'}


def equipment_options(draft):
    draft=validate(draft)
    groups=[_group(table,table,draft['gear'][table]) for table in GEAR_TABLES]
    if draft['bonus'] is not None:groups.append(_group('bonus',draft['bonus']['table'],draft['bonus']['raw']))
    return groups


def preview(draft,choices,actor):
    """Rebuild from persisted rolls. No randomness or remote access on review."""
    draft=validate(draft)
    if draft['owner']!=actor:raise PermissionError('No controlas este borrador de personaje')
    if not isinstance(choices,dict) or set(choices)-{'swap','identity','weapons','disposition'}:
        raise ValueError('Opciones de creación de Cairn inválidas')
    core=rules.core_from_rolls(draft['core'])
    swap=choices.get('swap',[])
    if not isinstance(swap,list):raise ValueError('Intercambio inicial inválido')
    if swap:core=rules.swap_initial(core,swap)
    identity=copy.deepcopy(draft['identity']);selected=choices.get('identity',{})
    if not isinstance(selected,dict) or set(selected)-{'name','surname','background'}:raise ValueError('Elecciones de identidad inválidas')
    identity.update(selected)
    resolved=rules.identity_from_rolls(draft['nameTable'],identity['name'],identity['surname'],identity['background'],identity['traits'])
    core.update({k:resolved[k] for k in ('name','background','traits')})
    core['owner']=actor
    weapons=choices.get('weapons',{});disposition=choices.get('disposition',{})
    if not isinstance(weapons,dict) or not isinstance(disposition,dict):raise ValueError('Elecciones de equipo inválidas')
    gear=[{'id':'rations','item':'Rations (three days)','state':'carried'},
        {'id':'torch','item':'Torch','state':'carried'}]
    pending=[];weapon_groups=set()
    if draft['bonus'] is None:pending.append('bonusTable')
    for group in equipment_options(draft):
        options=group['options']
        if group['chooseOne']:
            weapon_groups.add(group['id']);choice=weapons.get(group['id'])
            if choice is None:pending.append('weapon:'+group['id']);continue
            if not isinstance(choice,str) or choice not in options:raise ValueError('Arma fuera del resultado original')
            options=[choice]
        for index,name in enumerate(options):
            gear.append({'id':group['id']+':'+str(index),'item':name,'state':'carried'})
    if set(weapons)-weapon_groups:raise ValueError('Elección de arma sin tirada correspondiente')
    ids={v['id'] for v in gear}
    if set(disposition)-ids:raise ValueError('No puedes añadir equipo ajeno a los resultados')
    for entry in gear:entry['state']=disposition.get(entry['id'],entry['state'])
    core=inventory.apply_inventory(core,gear)
    core['creation'].update(complete=False,pending=pending,draft=copy.deepcopy(draft),choices=copy.deepcopy(choices),
        identity=resolved['provenance'])
    return core


def finalize(draft,choices,actor):
    """Confirm creation only; completion does not imply a complete game adapter."""
    core=preview(draft,choices,actor)
    if core['creation']['pending']:raise ValueError('Resuelve las elecciones pendientes antes de confirmar el personaje')
    core['creation']['complete']=True
    core['maxAbilities']=copy.deepcopy(core['abilities'])
    core['maxHitProtection']=core['initialHitProtection']
    return core


def validate_created(character):
    if not isinstance(character,dict) or not isinstance(character.get('creation'),dict):raise ValueError('Ficha de Cairn sin origen de creación')
    creation=character['creation'];identifier=character.get('id')
    if not isinstance(identifier,str) or not identifier or len(identifier)>200:raise ValueError('Identificador de personaje inválido')
    expected=finalize(creation.get('draft'),creation.get('choices'),character.get('owner'))
    expected['id']=identifier
    if character!=expected:raise ValueError('La ficha no coincide con sus resultados y elecciones iniciales verificadas')
    return copy.deepcopy(expected)


def draft_action(state,body,actor,draw=None):
    """Adapter action boundary; outer campaign transaction owns CAS and action IDs."""
    if not isinstance(state,dict) or state.get('ruleset')!=rules.ID:raise ValueError('La campaña no pertenece a Cairn 1e')
    if not isinstance(actor,str) or not actor or len(actor)>100:raise PermissionError('Identidad de jugador inválida')
    if not isinstance(body,dict):raise ValueError('Acción de creador inválida')
    drafts=state.get('creationDrafts',{})
    if not isinstance(drafts,dict):raise ValueError('Registro de borradores inválido')
    kind=body.get('type')
    if kind=='begin_character':
        if set(body)!={'type','nameTable'}:raise ValueError('La creación no admite estadísticas ni propietario del cliente')
        if actor in drafts:raise ValueError('Ya tienes un borrador; recupera sus tiradas originales')
        if len(drafts)>=100 or len(drafts)+len(state.get('importedDrafts',{}))>=400:raise ValueError('Límite de borradores de la campaña alcanzado')
        changed=begin(actor,body['nameTable'],draw)
    elif kind=='choose_bonus':
        if set(body)!={'type','table'}:raise ValueError('La elección adicional solo admite una tabla disponible')
        if actor not in drafts:raise ValueError('No tienes un borrador de personaje')
        changed=choose_bonus(drafts[actor],body['table'],actor,draw)
    else:raise ValueError('Acción de creador no disponible')
    result=copy.deepcopy(state);result.setdefault('creationDrafts',{})[actor]=changed
    return result


def preview_for_actor(state,choices,actor):
    """Read-only boundary: never select another player's draft, including for host."""
    if not isinstance(state,dict) or state.get('ruleset')!=rules.ID:raise ValueError('La campaña no pertenece a Cairn 1e')
    if not isinstance(actor,str) or actor not in state.get('creationDrafts',{}):raise PermissionError('No tienes acceso a un borrador propio')
    return preview(state['creationDrafts'][actor],choices,actor)
