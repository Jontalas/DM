"""Compile explicitly supplied NPC preparation without inference or new dice.

This is an authoring building block, not a public campaign action. It reuses
the package's complete NPC profiles and never accepts raw sheet statistics.
"""
import copy
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError
import rule_pack_actors as actors
import rule_pack_world as world

FORMAT='cronicas-adventure-actors-1'
MAX_BYTES=60000


def compile_preparation(preparation,pack,policy,player_ids=()):
    if policy!='provided-profile':raise RulePackError('Confirma el permiso de uso de los perfiles aportados')
    try:size=len(canonical(preparation).encode('utf-8'))
    except (TypeError,ValueError,RecursionError):raise RulePackError('Preparación de PNJ no serializable') from None
    if size>MAX_BYTES:raise RulePackError('Preparación de PNJ demasiado grande')
    if not isinstance(preparation,dict) or set(preparation)!={'format','package','npcs','actors'} or preparation['format']!=FORMAT:
        raise RulePackError('Formato de preparación de PNJ incompatible')
    if preparation['package']!={'id':pack.id,'version':pack.version,'sha256':pack.digest}:
        raise RulePackError('Los PNJ requieren otra versión exacta del paquete')
    npcs=world.validate(preparation['npcs']);definitions=preparation['actors']
    if not isinstance(definitions,list) or not 1<=len(definitions)<=actors.MAX_ACTORS:
        raise RulePackError('Actores de preparación fuera de límites')
    result=[]
    for definition in definitions:
        if not isinstance(definition,dict) or set(definition)!={'id','npc','profile','stages','publicFields'}:
            raise RulePackError('Definición de actor incompleta; no se admiten estadísticas directas')
        result.append(actors.create(pack,definition['id'],definition['npc'],definition['profile'],definition['stages'],
            definition['publicFields'],npcs,policy))
    # No introducedAt here: an uninstalled preparation has no campaign history.
    # Installation must assign the real message position in the atomic start.
    actors.validate_registry(result,pack,npcs,player_ids)
    return copy.deepcopy({'npcs':npcs,'actors':result})
