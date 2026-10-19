import sys,json,pathlib
sys.path.insert(0,'.deps')
import pymupdf
books=[('trey','Trey.pdf'),('reglas','Pathfinder_en_escastellano_subido para_elgrimorio.pdf'),('bestiario','bestiario pathfinder spanish [Unlocked by www.freemypdf.com].pdf')]
for key,name in books:
 r=pymupdf.open(pathlib.Path.home()/'Desktop'/name)
 pages=[{'page':i+1,'text':v.get_text()} for i,v in enumerate(r)]
 pathlib.Path('data/'+key+'.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
 print(key,len(pages),'empty',sum(len(v['text'].strip())<40 for v in pages),flush=True)
 print('\n'.join(v['text'] for v in pages[:4])[:5000],flush=True)
