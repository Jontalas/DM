"""Pruebas básicas: modificadores de ficha, sin IA ni efectos inventados."""
ABILITY_KEYS=('str','dex','con','int','wis','cha')
ABILITY_NAMES=('Fuerza','Destreza','Constitución','Inteligencia','Sabiduría','Carisma')
SAVE_KEYS=('fort','ref','will')
SAVE_NAMES=('Fortaleza','Reflejos','Voluntad')


def integer(value,low=-1000,high=1000):
    if type(value)!=int or not low<=value<=high:raise ValueError('Valor de prueba inválido')
    return value


def skill_totals(value):
    if not isinstance(value,list) or len(value)>50:raise ValueError('Máximo 50 habilidades preparadas')
    names=set();result=[]
    for row in value:
        if not isinstance(row,dict):raise ValueError('Habilidad inválida')
        name=row.get('name','')
        if not isinstance(name,str) or not name.strip() or len(name)>80:raise ValueError('Nombre de habilidad inválido')
        name=name.strip()
        if name.casefold() in names:raise ValueError('Habilidad duplicada')
        names.add(name.casefold());result.append({'name':name,'total':integer(row.get('total'))})
    return result


def modifier(character,kind,key):
    if character.get('hp',1)<0:raise ValueError('El estado del personaje requiere una resolución asistida para esta prueba')
    if character.get('conditions','').strip():raise ValueError('Las condiciones anotadas requieren revisar la prueba mediante resolución asistida')
    if kind=='ability' and key in ABILITY_KEYS:
        i=ABILITY_KEYS.index(key);score=integer(character['abilities'][i],1,60)
        return (score-10)//2,ABILITY_NAMES[i],f'{ABILITY_NAMES[i]} {score}: suelo(({score} − 10) / 2)'
    if kind=='save' and key in SAVE_KEYS:
        i=SAVE_KEYS.index(key);saves=character.get('saves')
        if not isinstance(saves,list) or len(saves)!=3:raise ValueError('Revisa las tres salvaciones de la ficha')
        return integer(saves[i]),SAVE_NAMES[i],'Total de salvación declarado en la ficha; ya incluye característica y otros modificadores'
    if kind=='skill':
        for row in skill_totals(character.get('skillTotals',[])):
            if row['name']==key:return row['total'],row['name'],'Total de habilidad preparado en la ficha; incluye todos sus modificadores y requisitos verificados'
    raise ValueError('Prueba no preparada en esta ficha')


def resolve(character,kind,key,raw,dc=None):
    bonus,name,basis=modifier(character,kind,key);integer(raw,1,20)
    if dc is not None:integer(dc,0,1000)
    success=None if dc is None else raw+bonus>=dc
    natural=None
    if kind=='save' and dc is not None and raw in (1,20):success=raw==20;natural='éxito automático' if success else 'fallo automático'
    return {'character':character['id'],'kind':kind,'key':key,'name':name,'die':raw,'modifier':bonus,'total':raw+bonus,'dc':dc,'success':success,'natural':natural,'basis':basis}
