"""Bounded immutable private workspace assets, separate from gameplay snapshots."""
import copy
import hashlib
import json
import re
import zlib
import rule_preparation_workspace as workspaces
from rule_pack_authoring import canonical
from rule_pack_runtime import RulePackError

FORMAT='cronicas-rule-workspace-ref-1'


def validate_ref(reference):
    if not isinstance(reference,dict) or set(reference)!={'format','sha256'} or reference['format']!=FORMAT or not isinstance(reference['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',reference['sha256']):raise RulePackError('Referencia privada de preparaciones inválida')
    return reference


def decode(reference,packed):
    validate_ref(reference)
    if not isinstance(packed,bytes) or len(packed)>workspaces.MAX_BYTES+1000:raise RulePackError('Datos privados fuera de límites')
    try:
        decoder=zlib.decompressobj();raw=decoder.decompress(packed,workspaces.MAX_BYTES+1)
        if len(raw)>workspaces.MAX_BYTES or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:raise RulePackError('El almacén privado supera su límite o está incompleto')
        if hashlib.sha256(raw).hexdigest()!=reference['sha256']:raise RulePackError('El almacén privado no coincide con su huella')
        workspace=json.loads(raw);workspaces.validate(workspace)
        return raw
    except (zlib.error,UnicodeError,ValueError,TypeError) as error:
        raise RulePackError('No se puede recuperar un almacén privado íntegro') from error


def detach(state):
    """Return light state plus an optional asset; never modify the input."""
    if state.get('ruleset')!='rule-pack':return state,None
    workspace=state.get('authoringWorkspace');legacy=state.get('authoring')
    reference=state.get('authoringWorkspaceRef')
    if reference is not None:validate_ref(reference)
    if workspace is None and legacy is None:return state,None
    if workspace is not None and legacy is not None:raise RulePackError('Preparaciones duplicadas en dos representaciones')
    if workspace is None:workspace=workspaces.from_legacy(legacy)
    workspaces.validate(workspace)
    raw=canonical(workspace).encode('utf-8');reference={'format':FORMAT,'sha256':hashlib.sha256(raw).hexdigest()}
    light=copy.deepcopy(state);light['authoring']=None;light['authoringWorkspace']=None;light['authoringWorkspaceRef']=reference
    return light,{'reference':reference,'raw':raw,'packed':zlib.compress(raw)}
