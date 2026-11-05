"""Bounded interpreter for versioned rule data. No eval, plugins, I/O or AI.

This kernel knows operations, never game names. Importing a document does not
certify its interpretation: source review and package verification are separate.
"""
import copy
import hashlib
import json
import re
import secrets
from bisect import bisect_right

FORMAT='cronicas-rules-1'
CAPABILITIES={'scalar-fields','expressions','tables','dice','actions','triggers','character-creation','staged-character-creation','action-results'}
LIMIT=10**12
OPS={'add':(1,20),'sub':(2,2),'mul':(2,2),'floor_div':(2,2),'min':(1,20),'max':(1,20),
     'eq':(2,2),'ne':(2,2),'lt':(2,2),'le':(2,2),'gt':(2,2),'ge':(2,2),
     'and':(1,20),'or':(1,20),'not':(1,1),'if':(3,3),'concat':(1,20)}


class RulePackError(ValueError):pass


def _fail(message):raise RulePackError(message)


def _integer(value):
    if type(value)!=int or abs(value)>LIMIT:_fail('Se esperaba un entero dentro de los límites del motor')
    return value


def _boolean(value):
    if type(value)!=bool:_fail('Se esperaba una condición booleana, no una equivalencia numérica')
    return value


def _scalar(value):
    if value is None or type(value)==bool:return value
    if type(value)==int:return _integer(value)
    if type(value)==str and len(value)<=4000:return value
    _fail('Valor de reglas no escalar o fuera de límites')


def _keys(value,required,optional=()):
    if not isinstance(value,dict) or not set(required)<=set(value) or set(value)-set(required)-set(optional):
        _fail('Campos incompletos o desconocidos en la definición de reglas')


def _id(value):
    if not isinstance(value,str) or not re.fullmatch('[a-z][a-z0-9_-]{0,63}',value):_fail('Identificador de reglas inválido')
    return value


def _text(value,limit=200):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:_fail('Texto identificativo de reglas inválido')
    return value


def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:_fail('El archivo contiene claves JSON duplicadas')
        result[key]=value
    return result


def read_document(raw):
    try:
        if isinstance(raw,dict):raw=json.dumps(raw,ensure_ascii=False,allow_nan=False)
        if isinstance(raw,bytes):raw=raw.decode('utf-8')
        if not isinstance(raw,str) or len(raw.encode('utf-8'))>256000:_fail('El paquete supera 256.000 bytes o no es JSON UTF-8')
        return json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _: _fail('Constante JSON no permitida'))
    except RulePackError:raise
    except (UnicodeError,TypeError,RecursionError,ValueError) as error:
        raise RulePackError('No se puede leer el paquete de reglas') from error


class RulePack:
    def __init__(self,raw):
        self._data=read_document(raw)
        data=self._data
        _keys(data,('format','id','version','engineVersion','name','edition','license','sources','coverage','requires','fields','tables','actions','triggers'),('creation',))
        if data['format']!=FORMAT or type(data['engineVersion'])!=int or data['engineVersion']!=1:_fail('Versión del motor de paquetes no compatible')
        self.id=_id(data['id']);self.version=_text(data['version'],40)
        if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',self.version):_fail('Versión de paquete inválida; usa mayor.menor.revisión')
        _text(data['name']);_text(data['edition'])
        _keys(data['license'],('id','attribution'),('url',))
        _text(data['license']['id']);_text(data['license']['attribution'],2000)
        if 'url' in data['license']:_text(data['license']['url'],1000)
        _keys(data['coverage'],('implemented','pending'))
        for entries in data['coverage'].values():
            if not isinstance(entries,list) or len(entries)>100:_fail('Cobertura declarada inválida')
            for entry in entries:_text(entry,500)
        required=data['requires']
        if not isinstance(required,list) or len(required)>32 or any(not isinstance(v,str) for v in required) or len(set(required))!=len(required):_fail('Capacidades requeridas inválidas')
        for capability in required:_id(capability)
        missing=set(required)-CAPABILITIES
        if missing:_fail('Operaciones del motor todavía no disponibles: '+', '.join(sorted(missing)))
        self._source_ids=set()
        if not isinstance(data['sources'],list) or not 1<=len(data['sources'])<=100:_fail('Faltan fuentes trazables')
        for source in data['sources']:
            _keys(source,('id','title','edition','locator'),('url',))
            identifier=_id(source['id'])
            if identifier in self._source_ids:_fail('Fuente duplicada')
            self._source_ids.add(identifier)
            for key in ('title','edition','locator'):_text(source[key],1000)
            if 'url' in source:_text(source['url'],1000)
        for key,maximum in [('fields',128),('tables',64),('actions',128),('triggers',64)]:
            value=data[key]
            if not isinstance(value,dict) or len(value)>maximum:_fail('Catálogo de '+key+' fuera de límites')
            for identifier in value:_id(identifier)
        if not data['fields'] or not data['actions']:_fail('El paquete necesita campos y acciones')
        self._nodes=0
        fields=set(data['fields'])
        for spec in data['fields'].values():
            _keys(spec,('type','label','sources'),('initial','derive','min','max','options','maxLength'))
            if ('initial' in spec)==('derive' in spec):_fail('Un campo necesita valor inicial o fórmula derivada, exclusivamente')
            self._definition(spec);self._sources(spec)
            if 'initial' in spec:self._value(spec,spec['initial'])
        self._table_index={}
        for table_id,table in data['tables'].items():
            _keys(table,('label','sources','rows'));_text(table['label']);self._sources(table)
            if not isinstance(table['rows'],list) or not 1<=len(table['rows'])<=2000:_fail('Tabla vacía o demasiado grande')
            for row in table['rows']:
                _keys(row,('min','max','value'));_integer(row['min']);_integer(row['max']);_scalar(row['value'])
            previous=None;ordered=sorted(table['rows'],key=lambda r:r['min'])
            for row in ordered:
                lo=row['min'];hi=row['max']
                if lo>hi or previous is not None and lo<=previous:_fail('Intervalos de tabla superpuestos o invertidos')
                previous=hi
            self._table_index[table_id]=([row['min'] for row in ordered],ordered)
        for spec in data['fields'].values():
            if 'derive' in spec:self._expression(spec['derive'],{'fields':fields})
        self._order=self._derived_order()
        for action in data['actions'].values():
            _keys(action,('label','sources','inputs','requires','rolls','effects'),('permission','resultFields'))
            _text(action['label']);self._sources(action)
            if action.get('permission','owner') not in ('owner','host'):_fail('Permiso de acción no compatible')
            if not isinstance(action['inputs'],dict) or len(action['inputs'])>32:_fail('Entradas de acción fuera de límites')
            for key,spec in action['inputs'].items():
                _id(key);_keys(spec,('type','label'),('min','max','options','maxLength','default'));self._definition(spec)
                if 'default' in spec:self._value(spec,spec['default'])
            scopes={'fields':fields,'inputs':set(action['inputs'])}
            self._expressions(action['requires'],scopes,32)
            if not isinstance(action['rolls'],list) or len(action['rolls'])>32:_fail('Demasiadas tiradas en una acción')
            rolls=set()
            for roll in action['rolls']:
                _keys(roll,('id','count','sides','keep'),('keepCount','when'))
                identifier=_id(roll['id'])
                if identifier in rolls:_fail('Tirada duplicada')
                if roll['keep'] not in ('all','highest','lowest'):_fail('Selección de dados no compatible')
                if 'keepCount' in roll:
                    if roll['keep']=='all' or type(roll['keepCount'])!=int or not 1<=roll['keepCount']<=100:_fail('Cantidad de dados conservados inválida')
                self._expression(roll['count'],scopes);self._expression(roll['sides'],scopes)
                self._expression(roll.get('when',True),{**scopes,'rolls':rolls})
                rolls.add(identifier)
            self._effects(action['effects'],{**scopes,'rolls':rolls})
            if 'resultFields' in action:
                results=action['resultFields']
                if not isinstance(results,list) or not 1<=len(results)<=16 or any(not isinstance(field,str) or field not in fields for field in results) or len(set(results))!=len(results):
                    _fail('Las salidas relevantes necesitan entre uno y dieciséis campos existentes distintos')
        for trigger in data['triggers'].values():
            _keys(trigger,('label','sources','when','effects'));_text(trigger['label']);self._sources(trigger)
            self._expression(trigger['when'],{'fields':fields});self._effects(trigger['effects'],{'fields':fields})
        self.creation=None;self.creation_steps=[]
        if 'creation' in data:
            if isinstance(data['creation'],dict) and 'steps' in data['creation']:
                _keys(data['creation'],('steps',));steps=data['creation']['steps']
                if not isinstance(steps,list) or not 1<=len(steps)<=12:_fail('La creación necesita entre una y doce etapas')
                self.creation_steps=[_id(step) for step in steps]
                if len(set(self.creation_steps))!=len(self.creation_steps):_fail('Las etapas de creación no pueden repetirse')
            else:
                _keys(data['creation'],('action',));self.creation_steps=[_id(data['creation']['action'])]
            for action in self.creation_steps:
                if action not in data['actions'] or data['actions'][action].get('permission','owner')!='owner':_fail('Cada etapa debe referir a una acción del propietario')
            self.creation=self.creation_steps[0]
        used={'scalar-fields','expressions','actions'}
        if self.creation is not None:used.add('character-creation')
        if 'steps' in data.get('creation',{}):used.add('staged-character-creation')
        if any('resultFields' in action for action in data['actions'].values()):used.add('action-results')
        if data['tables']:used.add('tables')
        if data['triggers']:used.add('triggers')
        if any(action['rolls'] for action in data['actions'].values()):used.add('dice')
        if used-set(required):_fail('El paquete usa capacidades que no declara: '+', '.join(sorted(used-set(required))))
        canonical=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.digest=hashlib.sha256(canonical).hexdigest()
        self.new_sheet('validation') # Also validates derived defaults and ranges.

    def document(self):return copy.deepcopy(self._data)

    def _sources(self,spec):
        refs=spec['sources']
        if not isinstance(refs,list) or not refs or any(not isinstance(v,str) or v not in self._source_ids for v in refs):_fail('Referencia reglamentaria inexistente')

    def _definition(self,spec):
        _text(spec['label'])
        if spec['type'] not in ('integer','boolean','text'):_fail('Tipo de campo no compatible')
        if spec['type']!='integer' and ('min' in spec or 'max' in spec):_fail('Límites numéricos en un campo no numérico')
        if 'min' in spec:_integer(spec['min'])
        if 'max' in spec:_integer(spec['max'])
        if spec.get('min',-LIMIT)>spec.get('max',LIMIT):_fail('Límites de campo invertidos')
        if 'maxLength' in spec and (spec['type']!='text' or type(spec['maxLength'])!=int or not 0<=spec['maxLength']<=4000):_fail('Longitud de texto inválida')
        if 'options' in spec:
            if not isinstance(spec['options'],list) or not 1<=len(spec['options'])<=100:_fail('Opciones de campo inválidas')
            for option in spec['options']:self._value({k:v for k,v in spec.items() if k!='options'},option)

    def _value(self,spec,value):
        kind=spec['type']
        if kind=='integer':
            _integer(value)
            if not spec.get('min',-LIMIT)<=value<=spec.get('max',LIMIT):_fail('Valor de campo fuera de sus límites')
        elif kind=='boolean':_boolean(value)
        elif not isinstance(value,str) or len(value)>spec.get('maxLength',4000):_fail('Texto de campo fuera de límites')
        if 'options' in spec and value not in spec['options']:_fail('Valor fuera de las opciones legales')
        return value

    def _expressions(self,items,scopes,maximum):
        if not isinstance(items,list) or len(items)>maximum:_fail('Lista de expresiones fuera de límites')
        for item in items:self._expression(item,scopes)

    def _expression(self,node,scopes,depth=0):
        self._nodes+=1
        if self._nodes>10000 or depth>20:_fail('El paquete supera la complejidad admitida')
        if not isinstance(node,dict):_scalar(node);return
        if 'ref' in node:
            _keys(node,('ref',));path=node['ref']
            if (not isinstance(path,list) or not 2<=len(path)<=5 or not isinstance(path[0],str) or path[0] not in scopes
                or not isinstance(path[1],str) or path[1] not in scopes[path[0]]):_fail('Referencia de expresión no disponible en esta fase')
            if path[0]!='rolls' and len(path)!=2:_fail('Solo las tiradas tienen propiedades anidadas')
            if path[0]=='rolls':
                if len(path)<3 or path[2] not in ('total','values','kept','sides','rolled'):_fail('Propiedad de tirada no disponible')
                if len(path)>3 and (len(path)!=4 or path[2] not in ('values','kept') or type(path[3])!=int or not 0<=path[3]<100):_fail('Índice de dado inválido')
            return
        if 'table' in node:
            _keys(node,('table','at'))
            if not isinstance(node['table'],str) or node['table'] not in self._data['tables']:_fail('Tabla referenciada inexistente')
            self._expression(node['at'],scopes,depth+1);return
        _keys(node,('op','args'));op=node['op'];args=node['args']
        if not isinstance(op,str) or op not in OPS:_fail('Operación de expresión no disponible')
        if not isinstance(args,list) or not OPS[op][0]<=len(args)<=OPS[op][1]:_fail('Número de operandos inválido')
        for arg in args:self._expression(arg,scopes,depth+1)

    def _effects(self,effects,scopes):
        if not isinstance(effects,list) or len(effects)>128:_fail('Efectos fuera de límites')
        targets=set()
        for effect in effects:
            _keys(effect,('field','value'),('when',));field=effect['field']
            if not isinstance(field,str) or field not in self._data['fields'] or 'derive' in self._data['fields'][field]:_fail('Destino de efecto inexistente o derivado')
            if field in targets:_fail('Un lote de efectos no puede asignar dos veces el mismo campo')
            targets.add(field);self._expression(effect['value'],scopes);self._expression(effect.get('when',True),scopes)

    def _derived_order(self):
        derived={key:spec['derive'] for key,spec in self._data['fields'].items() if 'derive' in spec}
        def refs(node):
            if not isinstance(node,dict):return set()
            if 'ref' in node:return {node['ref'][1]} if node['ref'][0]=='fields' else set()
            return set().union(*(refs(v) for v in node.get('args',[node.get('at')])) )
        visiting=set();done=set();order=[]
        def visit(key):
            if key in done:return
            if key in visiting:_fail('Las fórmulas derivadas contienen un ciclo')
            visiting.add(key)
            for dependency in sorted(refs(derived[key])&set(derived)):visit(dependency)
            visiting.remove(key);done.add(key);order.append(key)
        for key in derived:visit(key)
        return order

    def _eval(self,node,context,budget):
        budget[0]-=1
        if budget[0]<0:_fail('La resolución supera el presupuesto de cálculo')
        if not isinstance(node,dict):return node
        if 'ref' in node:
            value=context
            try:
                for key in node['ref']:value=value[key]
            except (KeyError,TypeError,IndexError):_fail('Valor requerido no disponible en esta resolución')
            return value
        if 'table' in node:
            value=_integer(self._eval(node['at'],context,budget))
            lower,rows=self._table_index[node['table']];index=bisect_right(lower,value)-1
            if index>=0 and value<=rows[index]['max']:return rows[index]['value']
            _fail('La tabla no cubre el resultado; no se ha inventado una equivalencia')
        op=node['op'];args=node['args']
        if op=='if':return self._eval(args[1] if _boolean(self._eval(args[0],context,budget)) else args[2],context,budget)
        if op=='and':return all(_boolean(self._eval(arg,context,budget)) for arg in args)
        if op=='or':return any(_boolean(self._eval(arg,context,budget)) for arg in args)
        values=[self._eval(arg,context,budget) for arg in args]
        if op=='not':return not _boolean(values[0])
        if op in ('eq','ne'):
            equal=type(values[0])==type(values[1]) and values[0]==values[1]
            return equal if op=='eq' else not equal
        if op=='concat':
            if any(not isinstance(v,str) for v in values):_fail('La concatenación solo admite textos')
            if sum(len(v) for v in values)>4000:_fail('El texto calculado supera el límite del motor')
            return _scalar(''.join(values))
        nums=[_integer(v) for v in values]
        if op=='add':result=sum(nums)
        elif op=='sub':result=nums[0]-nums[1]
        elif op=='mul':result=nums[0]*nums[1]
        elif op=='floor_div':
            if nums[1]==0:_fail('División por cero en una regla')
            result=nums[0]//nums[1]
        elif op=='min':result=min(nums)
        elif op=='max':result=max(nums)
        elif op=='lt':return nums[0]<nums[1]
        elif op=='le':return nums[0]<=nums[1]
        elif op=='gt':return nums[0]>nums[1]
        elif op=='ge':return nums[0]>=nums[1]
        else:_fail('Operación no compatible')
        return _integer(result)

    def _fields(self,stored,budget):
        specs=self._data['fields'];base={key for key,spec in specs.items() if 'initial' in spec}
        if not isinstance(stored,dict) or set(stored)!=base:_fail('La ficha no coincide con los campos almacenables del paquete')
        values={key:self._value(specs[key],value) for key,value in stored.items()}
        for key in self._order:values[key]=self._value(specs[key],self._eval(specs[key]['derive'],{'fields':values},budget))
        return values

    def new_sheet(self,owner):
        _text(owner,100)
        sheet={'format':'cronicas-sheet-1','package':{'id':self.id,'version':self.version,'sha256':self.digest if hasattr(self,'digest') else ''},
            'owner':owner,'revision':0,'fields':{key:copy.deepcopy(spec['initial']) for key,spec in self._data['fields'].items() if 'initial' in spec}}
        self._fields(sheet['fields'],[50000]);return sheet

    def view(self,sheet):
        fields=self._sheet(sheet)
        return {'package':copy.deepcopy(sheet['package']),'owner':sheet['owner'],'revision':sheet['revision'],'fields':fields}

    def create_character(self,owner,inputs=None,physical=None,draw=None):
        sheet=self.new_sheet(owner)
        if inputs is not None and not isinstance(inputs,dict) or physical is not None and not isinstance(physical,dict):_fail('Decisiones o dados de creación inválidos')
        if self.creation is None:
            if inputs or physical:_fail('Este paquete no define decisiones ni dados de creación')
            return sheet,None
        return self.execute(sheet,self.creation,{} if inputs is None else inputs,owner,
            physical=physical,draw=draw,creating=True)

    def creation_progress(self,sheet):
        self._sheet(sheet);completed=min(sheet['revision'],len(self.creation_steps))
        return {'complete':completed==len(self.creation_steps),'completed':completed,'total':len(self.creation_steps),
            'next':self.creation_steps[completed] if completed<len(self.creation_steps) else None}

    def ready(self,sheet):return self.creation_progress(sheet)['complete']

    def creation_inputs(self,sheet):
        progress=self.creation_progress(sheet)
        if progress['complete']:return {}
        action=self._data['actions'][progress['next']];inputs=copy.deepcopy(action['inputs'])
        fields=self._fields(sheet['fields'],[50000])
        def conditions(value):
            if isinstance(value,dict) and value.get('op')=='and':
                for argument in value['args']:yield from conditions(argument)
            else:yield value
        def has_inputs(value):
            if isinstance(value,dict):return value.get('ref',[None])[0]=='inputs' or any(has_inputs(child) for child in value.values())
            return isinstance(value,list) and any(has_inputs(child) for child in value)
        inverse={'le':'ge','lt':'gt','ge':'le','gt':'lt','eq':'eq'}
        for requirement in action['requires']:
            for condition in conditions(requirement):
                if not isinstance(condition,dict) or condition.get('op') not in inverse:continue
                left,right=condition['args'];op=condition['op']
                if not isinstance(left,dict) or left.get('ref',[None])[0]!='inputs':left,right=right,left;op=inverse[op]
                if not isinstance(left,dict) or set(left)!={'ref'} or len(left['ref'])!=2 or left['ref'][0]!='inputs' or has_inputs(right):continue
                key=left['ref'][1];spec=inputs[key]
                if spec['type']!='integer':continue
                try:value=self._eval(right,{'fields':fields},[50000])
                except (RulePackError,KeyError):continue
                if type(value)!=int:continue
                if op in ('le','lt','eq'):spec['max']=min(spec.get('max',LIMIT),value-(op=='lt'))
                if op in ('ge','gt','eq'):spec['min']=max(spec.get('min',-LIMIT),value+(op=='gt'))
        return inputs

    def advance_character(self,sheet,step,inputs,actor,physical=None,draw=None):
        return self.execute(sheet,step,inputs,actor,physical=physical,draw=draw,creating=True)

    def _sheet(self,sheet):
        _keys(sheet,('format','package','owner','revision','fields'))
        if sheet['format']!='cronicas-sheet-1' or sheet['package']!={'id':self.id,'version':self.version,'sha256':self.digest}:_fail('La ficha requiere otra versión o contenido del paquete')
        _text(sheet['owner'],100)
        if type(sheet['revision'])!=int or not 0<=sheet['revision']<=1000000:_fail('Revisión de ficha inválida')
        return self._fields(sheet['fields'],[50000])

    def _batch(self,stored,effects,context,budget):
        updates={}
        for effect in effects:
            if _boolean(self._eval(effect.get('when',True),context,budget)):
                field=effect['field'];updates[field]=self._value(self._data['fields'][field],self._eval(effect['value'],context,budget))
        result={**stored,**updates};self._fields(result,budget)
        return result,{key:{'before':stored[key],'after':value} for key,value in updates.items() if stored[key]!=value or type(stored[key])!=type(value)}

    def _prepare_action(self,sheet,action_id,inputs,actor,host=False,physical=None,creating=False):
        self._sheet(sheet)
        if type(creating)!=bool:_fail('Modo de creación inválido')
        if creating:
            if sheet['revision']>=len(self.creation_steps) or action_id!=self.creation_steps[sheet['revision']]:_fail('La etapa de creación no corresponde al progreso confirmado de esta ficha')
        elif action_id in self.creation_steps:_fail('Las acciones de creación solo se resuelven durante su etapa correspondiente')
        elif sheet['revision']<len(self.creation_steps):_fail('Completa la creación del personaje antes de jugar')
        if not isinstance(action_id,str) or action_id not in self._data['actions']:_fail('Acción no definida por este paquete')
        action=self._data['actions'][action_id]
        if not isinstance(actor,str) or not actor or len(actor)>100 or (action.get('permission','owner')=='owner' and actor!=sheet['owner']) or (action.get('permission')=='host' and host is not True):
            raise PermissionError('No tienes permiso para esta acción de la ficha')
        if not isinstance(inputs,dict) or set(inputs)-set(action['inputs']):_fail('Entradas desconocidas de acción')
        arguments={}
        for key,spec in action['inputs'].items():
            if key not in inputs and 'default' not in spec:_fail('Falta una decisión requerida por la acción: '+key)
            arguments[key]=self._value(spec,inputs.get(key,spec.get('default')))
        budget=[50000];fields=self._fields(sheet['fields'],budget);context={'fields':fields,'inputs':arguments,'rolls':{}}
        if not all(_boolean(self._eval(condition,context,budget)) for condition in action['requires']):_fail('La acción no cumple los requisitos de sus reglas')
        physical={} if physical is None else physical
        ids={r['id'] for r in action['rolls']}
        if not isinstance(physical,dict) or set(physical)-ids:_fail('Dados físicos sin tirada correspondiente')
        specs=[];potential=0
        for roll in action['rolls']:
            count=_integer(self._eval(roll['count'],context,budget));sides=_integer(self._eval(roll['sides'],context,budget))
            potential+=count
            if not 1<=count<=100 or not 2<=sides<=1000000 or potential>1000:_fail('Tirada fuera del presupuesto de dados')
            keep=count if roll['keep']=='all' else roll.get('keepCount',1)
            if keep>count:_fail('No puedes conservar más dados que los tirados')
            if roll['id'] in physical:
                values=physical[roll['id']]
                if not isinstance(values,list) or len(values)!=count or any(type(v)!=int or not 1<=v<=sides for v in values):_fail('Resultados físicos inválidos; no se ha tirado en el servidor')
            specs.append((roll,count,sides,keep))
        return arguments,budget,context,specs

    def preview(self,sheet,action_id,inputs,actor,host=False):
        arguments,_,_,specs=self._prepare_action(sheet,action_id,inputs,actor,host=host)
        return {'inputs':copy.deepcopy(arguments),'rolls':[{'id':roll['id'],'count':count,'sides':sides,'keep':keep} for roll,count,sides,keep in specs]}

    def execute(self,sheet,action_id,inputs,actor,host=False,physical=None,draw=None,creating=False):
        _,budget,context,specs=self._prepare_action(sheet,action_id,inputs,actor,host=host,physical=physical,creating=creating)
        physical={} if physical is None else physical
        action=self._data['actions'][action_id]
        draw=draw or (lambda sides:secrets.randbelow(sides)+1)
        trace={'action':action_id,'sources':copy.deepcopy(action['sources']),'rolls':{},'changes':{},'triggers':[]}
        for roll,count,sides,keep in specs:
            identifier=roll['id'];active=_boolean(self._eval(roll.get('when',True),context,budget))
            record={'rolled':active,'sides':sides,'values':[],'kept':[],'total':None}
            if active:
                values=list(physical[identifier]) if identifier in physical else [draw(sides) for _ in range(count)]
                if any(type(v)!=int or not 1<=v<=sides for v in values):_fail('El generador devolvió un dado inválido')
                kept=values if roll['keep']=='all' else sorted(values,reverse=roll['keep']=='highest')[:keep]
                record.update(values=values,kept=kept,total=sum(kept),origin='physical' if identifier in physical else 'server')
            context['rolls'][identifier]=record;trace['rolls'][identifier]=copy.deepcopy(record)
        stored,changes=self._batch(sheet['fields'],action['effects'],context,budget);trace['changes']=changes
        visited=set();applications=0
        while True:
            signature=json.dumps(stored,sort_keys=True,ensure_ascii=False)
            if signature in visited:_fail('Los desencadenantes forman un ciclo; no se ha aplicado la acción')
            visited.add(signature);changed=False
            for key,trigger in sorted(self._data['triggers'].items()):
                trigger_context={'fields':self._fields(stored,budget)}
                if _boolean(self._eval(trigger['when'],trigger_context,budget)):
                    updated,deltas=self._batch(stored,trigger['effects'],trigger_context,budget)
                    if deltas:
                        applications+=1
                        if applications>128:_fail('Los desencadenantes superan el presupuesto de resolución')
                        trace['triggers'].append({'id':key,'sources':copy.deepcopy(trigger['sources']),'changes':deltas})
                        stored=updated;changed=True
            if not changed:break
        result=copy.deepcopy(sheet);result['fields']=stored;result['revision']+=1
        values=self._sheet(result)
        if 'resultFields' in action:
            trace['results']={field:copy.deepcopy(values[field]) for field in action['resultFields']}
        return result,trace
