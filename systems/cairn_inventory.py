"""Experimental Cairn 1e inventory arithmetic, CC BY-SA 4.0.

Based on Cairn SRD v1.0 by Yochai Gal:
https://cairnrpg.com/first-edition/cairn-srd/#inventory
https://creativecommons.org/licenses/by-sa/4.0/
Changes: validated catalog, capacity/armor arithmetic, immutable state updates.
Not a complete equipment simulator: transport, bundling and casting remain pending.
"""
import copy
from functools import lru_cache
from systems import cairn_1e as cairn


@lru_cache(maxsize=1)
def _catalog():
    catalog={}
    for table in ('expeditionary-gear','tools','trinkets'):
        for raw in range(1,21):
            name=cairn.table_result(table,raw)
            catalog[name]={'name':name,'slots':1,'armor':0,'hands':0,'equip':False,'source':cairn.SOURCE+'#'+table}
    for name,slots,armor,hands in [('Brigandine',2,1,0),('Chainmail',2,2,0),('Plate',2,3,0),
            ('Gambeson',1,1,0),('Helmet',1,1,0),('Shield',1,1,1)]:
        catalog[name]={'name':name,'slots':slots,'armor':armor,'hands':hands,'equip':True,'source':cairn.SOURCE+'#armor-1'}
    for names,die,slots in [(['Dagger','Cudgel','Staff','Sickle'],6,1),
            (['Sword','Mace','Axe','Spear','Flail'],8,1),(['Halberd','War Hammer','Long Sword'],10,2),
            (['Sling'],4,1),(['Bow'],6,2),(['Crossbow'],8,2)]:
        for name in names:
            # "Bulky" establishes two slots, not an unconditional hand-use rule.
            catalog[name]={'name':name,'slots':slots,'armor':0,'hands':0,'equip':True,'requiresHandRuling':True,
                'damageDie':die,'source':cairn.SOURCE+'#weapons-1'}
    for name in ('Rations (three days)','Torch','Fatigue'):
        section='deprivation--fatigue' if name=='Fatigue' else 'starting-gear'
        catalog[name]={'name':name,'slots':1,'armor':0,'hands':1 if name=='Torch' else 0,'equip':name=='Torch','source':cairn.SOURCE+'#'+section}
    for raw in range(1,101):
        name='Spellbook: '+cairn.table_result('spellbooks-d100',raw)
        catalog[name]={'name':name,'slots':1,'armor':0,'hands':0,'equip':False,'spell':cairn.table_result('spellbooks-d100',raw),'source':cairn.SOURCE+'#spellbooks-d100'}
    # Do not guess whether the bulky cart itself uses its extra carrying slots.
    catalog['Cart (+4 slots, bulky)'].update(slots=2,requiresAdjudication=True)
    return catalog


def item(name):
    if not isinstance(name,str) or name not in _catalog():raise ValueError('Equipo de Cairn no verificado')
    return copy.deepcopy(_catalog()[name])


def apply_inventory(core,loadout):
    """Apply chosen carried gear. Unloading does not heal protection lost at full load."""
    if not isinstance(core,dict) or core.get('ruleset')!=cairn.ID:raise ValueError('La ficha no pertenece a Cairn 1e')
    hp=core.get('hitProtection')
    if type(hp)!=int or hp<0:raise ValueError('Protección de Cairn inválida')
    if not isinstance(loadout,list) or len(loadout)>100:raise ValueError('Inventario de Cairn inválido')
    ids=set();slots=0;armor=0;hands=0;equipped=[]
    for entry in loadout:
        if not isinstance(entry,dict) or set(entry)!={'id','item','state'}:raise ValueError('Entrada de inventario inválida')
        identifier=entry['id']
        if not isinstance(identifier,str) or not identifier or len(identifier)>80 or identifier in ids:raise ValueError('Objeto duplicado o sin identidad')
        ids.add(identifier);descriptor=item(entry['item'])
        if entry['state'] not in ('carried','equipped','stored'):raise ValueError('Estado de equipo inválido')
        if entry['state']=='stored':continue
        if descriptor.get('requiresAdjudication'):raise ValueError('Este equipo requiere resolver transporte; no se ha supuesto su capacidad')
        slots+=descriptor['slots']
        if entry['state']=='equipped':
            if descriptor.get('requiresHandRuling'):raise ValueError('El uso de manos del arma requiere una resolución contextual; solo se han verificado sus dados y espacios')
            if not descriptor['equip']:raise ValueError('El uso de este objeto todavía no está implementado; puede transportarse')
            equipped.append(descriptor['name']);armor+=descriptor['armor'];hands+=descriptor['hands']
    if slots>10:raise ValueError('El equipo transportado ocupa '+str(slots)+' de diez espacios; elige qué guardar o dejar')
    if hands>2:raise ValueError('El equipo seleccionado requiere más de dos manos')
    if any(equipped.count(name)>1 for name in ('Helmet','Shield')):
        raise ValueError('Esta combinación repetida de protecciones requiere adjudicación; no se han sumado sus bonos')
    result=copy.deepcopy(core);result['inventory']=copy.deepcopy(loadout)
    result['inventorySlots']=slots;result['armor']=min(3,armor)
    if slots==10:result['hitProtection']=0
    return result
