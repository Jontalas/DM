"""Deterministic first aid primitive, Core PDF93/94/190-191.

Caller owns permissions, a safe adjacent scene, initiative and RNG. This block
only covers a dying patient, not bleeding, long-term care or daily recovery.
It returns copies; no IO, rolls, logging, turn advancement or player choices.
"""
import copy
import checks
import combat
import pf_recovery


def validate(helper,patient,spent,*,round_number,order,epoch=None):
    if helper['id']==patient['id'] or not combat.standing(helper):raise ValueError('Los primeros auxilios requieren otra ficha consciente que pueda ayudar')
    if any(c.get('conditions','').strip() for c in (helper,patient)):raise ValueError('Resuelve las condiciones antes de aplicar primeros auxilios')
    if combat.health_status(patient)!='moribundo':raise ValueError('Este bloque de auxilio requiere un paciente moribundo')
    if max(abs(helper['x']-patient['x']),abs(helper['y']-patient['y']))!=1:raise ValueError('Este bloque de primeros auxilios requiere un paciente adyacente')
    if spent.get('standard') or helper['hp']<=0 and spent.get('move'):raise ValueError('No queda la acción estándar necesaria para primeros auxilios')
    checks.modifier(helper,'skill','Curar')
    # Validate the prospective care clock even when a future roll would fail.
    # A legacy clock without an epoch remains care-2, never a guessed care-3.
    prospective=copy.deepcopy(patient)
    pf_recovery.record_stabilization(prospective,assisted=True,round_number=round_number,initiative=helper['id'],order=order,epoch=epoch)


def resolve(helper,patient,spent,*,round_number,order,epoch=None,die):
    validate(helper,patient,spent,round_number=round_number,order=order,epoch=epoch)
    check=checks.resolve(helper,'skill','Curar',checks.integer(die,1,20),15)
    healer,target,budget=copy.deepcopy(helper),copy.deepcopy(patient),copy.deepcopy(spent)
    budget['standard']=True
    if check['success']:
        pf_recovery.record_stabilization(target,assisted=True,round_number=round_number,initiative=healer['id'],order=order,epoch=epoch)
    if healer['hp']<=0:
        healer['hp']-=1;healer['stable']=False;pf_recovery.clear_episode(healer)
    return {'helper':healer,'patient':target,'spent':budget,'check':check}
