"""Creación validada: humano guerrero 1, compra de 20 puntos y catálogo acotado."""
import copy
import json
from pathlib import Path

CATALOG=json.loads((Path(__file__).parent/'static/creation-catalog.json').read_text(encoding='utf-8'))


def build(choices):
    if not isinstance(choices,dict):raise ValueError('Elecciones de personaje inválidas')
    if choices.get('race','human')!='human' or choices.get('class','fighter')!='fighter' or type(choices.get('level',1))!=int or choices.get('level',1)!=1:
        raise ValueError('El creador automático admite por ahora humanos guerreros de nivel 1')
    name=choices.get('name','')
    if not isinstance(name,str) or not name.strip() or len(name)>80:raise ValueError('Elige un nombre de hasta 80 caracteres')
    base=choices.get('abilities');bonus=choices.get('bonus');favored=choices.get('favored','hp')
    if not isinstance(base,list) or len(base)!=6 or any(type(v)!=int or not 7<=v<=18 for v in base):raise ValueError('Características base entre 7 y 18')
    if type(bonus)!=int or not 0<=bonus<6 or favored not in ('hp','skill'):raise ValueError('Elección racial o clase predilecta inválida')
    spent=sum(CATALOG['costs'][str(v)] for v in base)
    if spent>CATALOG['budget']:raise ValueError('Superas los 20 puntos de características')
    attrs=base[:];attrs[bonus]+=2;mods=[(v-10)//2 for v in attrs]
    if attrs[0]<10:raise ValueError('Este bloque de combate requiere Fuerza 10 o más; el daño con penalizador aún no está automatizado')
    def selected(group,key):
        value=choices.get(key)
        if not isinstance(value,str) or value not in CATALOG[group]:raise ValueError('Opción de equipo no disponible')
        return CATALOG[group][value]
    weapon=selected('weapons','weapon');armor=selected('armors','armor');shield=selected('shields','shield')
    if weapon['hands']==2 and choices['shield']!='none':raise ValueError('Un arma a dos manos no permite este escudo')
    feats=choices.get('feats',[]);ranks=choices.get('skills',[]);languages=choices.get('languages',[])
    for values,allowed,limit in [(feats,CATALOG['feats'],3),(ranks,CATALOG['skills'],14),(languages,CATALOG['languages'],5)]:
        if not isinstance(values,list) or len(values)>limit or any(not isinstance(v,str) or v not in allowed for v in values) or len(set(values))!=len(values):raise ValueError('Elección duplicada o no disponible')
    if len(feats)!=3 or not any(CATALOG['feats'][f]['combat'] for f in feats):raise ValueError('Elige tres dotes distintas, al menos una de combate para el guerrero')
    skill_points=max(1,2+mods[3])+1+int(favored=='skill')
    if len(ranks)!=skill_points:raise ValueError(f'Asigna tus {skill_points} rangos: un rango por habilidad a nivel 1')
    if len(languages)!=max(0,mods[3]):raise ValueError('Elige un idioma adicional por cada punto de bonificador de Inteligencia')
    inventory=[weapon,armor,shield,CATALOG['kit'],CATALOG['outfit']]
    remaining=CATALOG['wealthCp']-sum(item['price'] for item in inventory)
    if remaining<0:raise ValueError('El equipo supera las 175 po iniciales')
    gold,small=divmod(remaining,100);silver,copper=divmod(small,10)
    weight=sum(item['weight'] for item in inventory)*100+(gold+silver+copper)*2
    limits=CATALOG['loads'][str(attrs[0])]
    load=next((i for i,limit in enumerate(limits) if weight<=limit*100),None)
    if load is None:raise ValueError('El equipo supera tu carga máxima')
    penalty=max(armor['penalty']+shield['penalty'],[0,3,6][load])
    dex=min(mods[1],armor['maxDex'],[99,3,1][load]);ac=10+armor['ac']+shield['ac']+dex
    damage_bonus=mods[0]*3//2 if weapon['hands']==2 else mods[0]
    skill_totals=[];skill_breakdown=[]
    for key,skill in CATALOG['skills'].items():
        rank=int(key in ranks)
        if skill.get('trained') and not rank:continue
        class_bonus=3 if rank and skill['class'] else 0;armor_penalty=penalty if skill['armor'] else 0
        total=mods[skill['ability']]+rank+class_bonus-armor_penalty
        skill_totals.append({'name':skill['name'],'total':total})
        skill_breakdown.append({'name':skill['name'],'ability':mods[skill['ability']],'rank':rank,'class':class_bonus,'penalty':armor_penalty,'total':total})
    hp=10+mods[2]+int(favored=='hp')+3*int('toughness' in feats)
    attack=1+mods[0]+int('focus' in feats)
    saves=[2+mods[2]+2*int('fortitude' in feats),mods[1]+2*int('reflexes' in feats),mods[4]+2*int('will' in feats)]
    data={'name':name.strip(),'race':'Humano','class':'Guerrero','level':1,'abilities':attrs,'maxHp':hp,'hp':hp,'ac':ac,
        'saves':saves,'speed':min(armor['speed'],6 if load==0 else 4),'initiative':mods[1]+4*int('initiative' in feats),
        'attack':attack,'damage':weapon['dice']+(f'+{damage_bonus}' if damage_bonus else ''),'skillTotals':skill_totals,
        'meleeProfile':{'flatAc':ac-max(0,dex),'criticalMin':weapon['criticalMin'],'multiplier':weapon['multiplier']},
        'feats':', '.join(CATALOG['feats'][f]['name'] for f in feats),'equipment':'; '.join(i['name'] for i in inventory if i['name']!='Sin escudo'),
        'load':f'{weight/100:.2f} libras; carga '+['ligera','media','pesada'][load],
        'resources':f'{gold} po, {silver} pp, {copper} pc','skills':'Totales calculados desde características, rangos, clase y penalizador de armadura/carga.',
        'notes':'Idiomas: '+', '.join(['Común',*languages])+'. Humano mediano adulto; arma seleccionada empuñada. Sin arquetipos ni rasgos alternativos.'}
    details={'pointCost':spent,'mods':mods,'armor':armor['ac'],'shield':shield['ac'],'dexAc':dex,'touchAc':10+dex,
        'weight':weight,'load':load,'penalty':penalty,'coins':[gold,silver,copper],'spentCp':CATALOG['wealthCp']-remaining,
        'skillPoints':skill_points,'skills':skill_breakdown,'damageBonus':damage_bonus,'hpClass':10,'hpCon':mods[2],
        'hpFavored':int(favored=='hp'),'hpFeat':3*int('toughness' in feats)}
    return data,{'version':1,'choices':copy.deepcopy(choices),'details':details}
