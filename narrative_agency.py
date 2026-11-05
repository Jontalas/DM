"""Conservative checks for explicit player execution before action resolution.

This detects a bounded Spanish pattern, not arbitrary semantic agency violations.
The director must describe the world/request and attribute choices as declarations.
"""
import re
from rule_pack_runtime import RulePackError

NAMED=r'(?:se acerca|se dirige|camina|avanza|entra|sale|corre|se mueve|se desplaza|cruza|abre|toma|coge|ataca|golpea|decide|piensa|siente|dice)\b'
SECOND=r'(?:te acercas|te diriges|caminas|avanzas|entras|sales|corres|te mueves|te desplazas|cruzas|abres|tomas|coges|atacas|golpeas|decides|piensas|sientes|dices)\b'


class NarrativeAgencyError(RulePackError):pass


def validate_pending_reply(request,reply):
    if request['operation']!='talk' or request['kind']!='action':return
    names=[actor['name'] for actor in request['party'] if len(actor['name'].strip())>1]
    named=re.compile(r'^\s*[«"“]?(?:'+('|'.join(re.escape(name) for name in names))+r')\s+'+NAMED,re.IGNORECASE) if names else None
    second=re.compile(r'^\s*[«"“]?'+SECOND,re.IGNORECASE)
    for key in ('narration','summary','preparation'):
        for sentence in re.split(r'(?<=[.!?])\s+|\n+',reply[key]):
            # Explicit questions/options are not assertions of execution.
            if sentence.lstrip().startswith('¿') or sentence.rstrip().endswith('?'):continue
            if second.search(sentence) or named and named.search(sentence):
                raise NarrativeAgencyError('El director presenta una acción o decisión del personaje como ejecutada antes de resolverla. La respuesta queda capturada; no se ha cambiado la partida ni repetido IA')
