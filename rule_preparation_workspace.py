"""Private normalized preparation store. No network, RNG or persistence.

Each source text is stored once. Blocks retain request metadata and reports;
their page entries reference the shared source pool. Expansion is read-only.
"""
import copy
import hashlib
from rule_pack_runtime import RulePackError
import rule_pack_authoring as authoring

FORMAT='cronicas-rule-workspace-1'
MAX_BLOCKS=128
MAX_SOURCES=4096
MAX_BYTES=750000


def empty():return {'format':FORMAT,'latest':None,'sources':{},'texts':{},'blocks':{}}


def _keys(value,keys):
    if not isinstance(value,dict) or set(value)!=set(keys):raise RulePackError('Campos del almacén de preparaciones inválidos')


def _size(value):
    if len(authoring.canonical(value).encode('utf-8'))>MAX_BYTES:raise RulePackError('El almacén de preparaciones alcanza su límite; conserva una copia antes de ampliar o archivar datos')


def _shape(workspace):
    _keys(workspace,('format','latest','sources','texts','blocks'))
    if workspace['format']!=FORMAT:raise RulePackError('Versión de almacén de preparaciones incompatible')
    if not isinstance(workspace['sources'],dict) or len(workspace['sources'])>MAX_SOURCES:raise RulePackError('Catálogo de fragmentos fuera de límites')
    if not isinstance(workspace['texts'],dict) or len(workspace['texts'])>MAX_SOURCES:raise RulePackError('Catálogo de textos fuera de límites')
    if not isinstance(workspace['blocks'],dict) or len(workspace['blocks'])>MAX_BLOCKS:raise RulePackError('Catálogo de bloques fuera de límites')
    latest=workspace['latest']
    if (workspace['blocks'] and (not isinstance(latest,str) or latest not in workspace['blocks'])) or (not workspace['blocks'] and latest is not None):raise RulePackError('La preparación más reciente no está en el almacén')


def _put(workspace,prepared,report):
    _shape(workspace);result=copy.deepcopy(workspace);digest=prepared['sha256']
    if digest in result['blocks']:raise RulePackError('Este bloque ya está preparado; consulta su informe sin repetir la llamada')
    if len(result['blocks'])>=MAX_BLOCKS:raise RulePackError('El almacén admite hasta 128 bloques; no se han eliminado preparaciones')
    request=copy.deepcopy(prepared['request']);references=[]
    for page,source,fragment in zip(request['document']['pages'],prepared['sources'],prepared['fragments']):
        identifier=source['id'];entry={'metadata':copy.deepcopy(source),'sha256':fragment['sha256']}
        if identifier in result['sources'] and authoring.canonical(result['sources'][identifier])!=authoring.canonical(entry):raise RulePackError('Una referencia de fragmento tiene contenido incompatible')
        if fragment['sha256'] in result['texts'] and result['texts'][fragment['sha256']]!=fragment['text']:raise RulePackError('Un texto no coincide con la huella compartida')
        result['texts'][fragment['sha256']]=fragment['text']
        result['sources'][identifier]=entry;references.append({'page':page['page'],'source':identifier})
    if len(result['sources'])>MAX_SOURCES:raise RulePackError('Demasiados fragmentos; no se han eliminado fuentes')
    request['document']['pages']=references
    result['blocks'][digest]={'request':request,'sha256':digest,'sourceScheme':prepared['sourceScheme'],'report':copy.deepcopy(report)}
    result['latest']=digest;_size(result);return result


def reserve(workspace,prepared):
    """Unpersistable capacity estimate, used before a potentially billable call."""
    return _put(workspace,prepared,'x'*(authoring.MAX_RESPONSE+12000))


def add(workspace,record):
    prepared=authoring.validate_record(record)
    return _put(workspace,prepared,record['report'])


def from_legacy(record):return empty() if record is None else add(empty(),record)


def expand(workspace,digest,verify_report=False):
    _shape(workspace)
    if not isinstance(digest,str) or digest not in workspace['blocks']:raise RulePackError('Bloque de preparación no disponible')
    compact=workspace['blocks'][digest];_keys(compact,('request','sha256','sourceScheme','report'))
    if compact['sha256']!=digest:raise RulePackError('La clave del bloque no coincide con su huella')
    request=copy.deepcopy(compact['request'])
    if not isinstance(request,dict) or not isinstance(request.get('document'),dict):raise RulePackError('Documento del bloque inválido')
    references=request['document'].get('pages')
    if not isinstance(references,list) or not 1<=len(references)<=32:raise RulePackError('Páginas del bloque inválidas')
    pages=[];entries=[]
    for reference in references:
        _keys(reference,('page','source'));identifier=reference['source']
        if not isinstance(identifier,str) or identifier not in workspace['sources']:raise RulePackError('Falta un fragmento del bloque')
        entry=workspace['sources'][identifier];_keys(entry,('metadata','sha256'))
        if not isinstance(entry['sha256'],str) or entry['sha256'] not in workspace['texts']:raise RulePackError('Falta el texto de un fragmento')
        text=workspace['texts'][entry['sha256']]
        if not isinstance(text,str) or len(text)>authoring.MAX_TEXT or hashlib.sha256(text.encode('utf-8')).hexdigest()!=entry['sha256']:raise RulePackError('El texto no coincide con su huella de fragmento')
        pages.append({'page':reference['page'],'text':text});entries.append(entry)
    request['document']['pages']=pages
    prepared=authoring.prepare_input(request,compact['sourceScheme'])
    if prepared['sha256']!=digest:raise RulePackError('El contenido no coincide con la preparación guardada')
    for reference,entry,source in zip(references,entries,prepared['sources']):
        if reference['source']!=source['id'] or authoring.canonical(entry['metadata'])!=authoring.canonical(source):raise RulePackError('El fragmento no corresponde a la referencia original')
    result={'request':request,'sha256':digest,'sourceScheme':compact['sourceScheme'],'report':copy.deepcopy(compact['report'])}
    if verify_report:authoring.validate_record(result)
    return result


def validate(workspace):
    _shape(workspace);_size(workspace);used=set()
    for digest in workspace['blocks']:
        expand(workspace,digest,verify_report=True)
        used.update(page['source'] for page in workspace['blocks'][digest]['request']['document']['pages'])
    if used!=set(workspace['sources']):raise RulePackError('Hay fragmentos sin bloque; no se conservan datos ocultos ni fuentes huérfanas')
    if {entry['sha256'] for entry in workspace['sources'].values()}!=set(workspace['texts']):raise RulePackError('Hay textos sin referencias; la copia contiene datos huérfanos')
