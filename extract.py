import sys,json,pathlib
sys.path.insert(0,'.deps')
from pypdf import PdfReader
books=[('trey','Trey.pdf'),('reglas','Pathfinder_en_escastellano_subido para_elgrimorio.pdf'),('bestiario','bestiario pathfinder spanish [Unlocked by www.freemypdf.com].pdf')]
for key,name in books:
 p=pathlib.Path.home()/'Desktop'/name
 r=PdfReader(p); pages=[{'page':i+1,'text':v.extract_text() or ''} for i,v in enumerate(r.pages)]
 pathlib.Path('data/'+key+'.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
 print(key,len(pages));print('\n'.join(v['text'] for v in pages[:4])[:6000])
