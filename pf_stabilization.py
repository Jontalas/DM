"""One dying creature's own-turn check, Core PDF191/printed190.

No initiative advancement, RNG, IO, logging or character decisions. Ongoing
damage and annotated conditions need an explicit caller resolution.
"""
import copy
import checks
import combat
import pf_recovery


def validate(patient,*,round_number,order,epoch=None):
    if patient.get('conditions','').strip():raise ValueError('Las condiciones necesitan resolución antes de estabilizar')
    if combat.health_status(patient)!='moribundo':raise ValueError('La comprobación requiere una criatura moribunda')
    prospective=copy.deepcopy(patient)
    pf_recovery.record_stabilization(prospective,assisted=False,round_number=round_number,initiative=patient['id'],order=order,epoch=epoch)


def resolve(patient,*,die,round_number,order,epoch=None):
    validate(patient,round_number=round_number,order=order,epoch=epoch)
    checks.integer(die,1,20);updated=copy.deepcopy(patient)
    modifier=(patient['abilities'][2]-10)//2+patient['hp']
    success=die==20 or die+modifier>=10
    if success:
        pf_recovery.record_stabilization(updated,assisted=False,round_number=round_number,initiative=patient['id'],order=order,epoch=epoch)
    else:updated['hp']-=1
    return {'patient':updated,'die':die,'modifier':modifier,'total':die+modifier,'dc':10,'success':success,
        'hpBefore':patient['hp'],'hpAfter':updated['hp'],'status':combat.health_status(updated)}
