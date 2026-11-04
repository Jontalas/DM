"""Explicit system identity and availability. Never infer cross-system equivalence."""
import copy

DEFAULT='pathfinder-1e'
SYSTEMS={DEFAULT:{'id':DEFAULT,'name':'Pathfinder 1e','edition':'Primera edición',
    'status':'partial','characterCreation':'Humanos guerreros de nivel 1',
    'coverage':['Pruebas de ficha preparadas','Combate cuerpo a cuerpo básico','Investigación de Percepción en entorno tranquilo'],
    'limits':['Otras clases y niveles','Conjuros','Cobertura completa de combate y exploración'],
    'companion':'TREY en su ámbito; no sustituye reglas de Pathfinder'}}


def require(identifier=DEFAULT):
    if not isinstance(identifier,str) or identifier not in SYSTEMS:
        raise ValueError('Ese sistema de juego todavía no está disponible; no se mezclarán sus reglas con Pathfinder')
    return copy.deepcopy(SYSTEMS[identifier])


def catalog():
    return [require(identifier) for identifier in SYSTEMS]


def identify(state):
    """Legacy campaigns belong to the original PF1 engine, without conversion."""
    if not isinstance(state,dict):raise ValueError('Estado de campaña inválido')
    descriptor=require(state.get('ruleset',DEFAULT))
    state.setdefault('ruleset',descriptor['id'])
    return descriptor


def new_campaign(config):
    descriptor=require(config.get('ruleset',DEFAULT))
    selected=adapter(descriptor['id'])
    if selected is not None:return selected.initial_state(config)
    from engine import initial_state
    state=initial_state(config);state['ruleset']=descriptor['id']
    return state


def adapter(identifier):
    """Availability is always checked before loading system-specific operations."""
    require(identifier)
    if identifier==DEFAULT:return None
    if identifier=='cairn-1e':
        from systems import cairn_engine
        return cairn_engine
    if identifier=='rule-pack':
        import rule_pack_campaign
        return rule_pack_campaign
    raise ValueError('El sistema no tiene un adaptador implementado')
