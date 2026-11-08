"""Source-backed PF initiative instants, not a complete rest/event controller.

Core PDF179/printed178:6s rounds, intervals ending at the same initiative.
Select whole simultaneous batches; never assign a priority by effect type.
"""
import copy


class SimultaneousEffects(ValueError):
    pass


def first_batch(events,*,epoch,order):
    """Return independent copies of every event at the earliest exact instant.

    Event payloads belong to their rule module. This function validates only
    the shared clock, not legality or the order of effects on one patient.
    """
    if not isinstance(events,list):raise ValueError('La agenda requiere una lista de sucesos')
    if not events:return []
    if (type(epoch)!=int or not 1<=epoch<=1000000 or not isinstance(order,list)
        or not 1<=len(order)<=400 or any(not isinstance(v,str) or not v for v in order)
        or len(set(order))!=len(order)):raise ValueError('Los sucesos necesitan un episodio y orden de iniciativa comunes')
    positions={identifier:i for i,identifier in enumerate(order)}
    for event in events:
        if (not isinstance(event,dict) or type(event.get('epoch'))!=int or event['epoch']!=epoch
            or type(event.get('round'))!=int or event['round']<1
            or not isinstance(event.get('initiative'),str) or event['initiative'] not in positions
            or type(event.get('orderIndex'))!=int or event['orderIndex']!=positions[event['initiative']]):
            raise ValueError('El instante no corresponde al reloj compartido')
    earliest=min((event['round'],event['orderIndex']) for event in events)
    return [copy.deepcopy(event) for event in events if (event['round'],event['orderIndex'])==earliest]


def require_non_overlapping(batch):
    """Reject multiple effects on one patient; do not invent their priority."""
    seen=set()
    for event in batch:
        target=event.get('character') if isinstance(event,dict) else None
        if not isinstance(target,str) or not target:raise ValueError('El efecto médico necesita un paciente identificado')
        if target in seen:raise SimultaneousEffects('Los efectos coincidentes sobre un paciente necesitan una resolución conjunta verificada')
        seen.add(target)


def elapsed_seconds(start,end):
    """Convert (round, order index) only when the initiative count is equal."""
    if any(not isinstance(point,tuple) or len(point)!=2 or any(type(v)!=int for v in point)
        or point[0]<1 or point[1]<0 for point in (start,end)):
        raise ValueError('El intervalo requiere rondas y cuentas de iniciativa conocidas')
    if end<start:raise ValueError('El reloj no puede retroceder')
    if start[1]!=end[1]:raise ValueError('No se convierte una fracción de iniciativa en segundos inventados')
    return (end[0]-start[0])*6
