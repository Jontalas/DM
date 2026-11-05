"""Local visual preview: disposable data, simulated director, no remote services.

Run .venv/Scripts/python.exe scripts/preview_local.py and open localhost:8765.
This deliberately reuses the browser-test sandbox, never production credentials.
"""
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['TEST_RULE_PACK_FIXTURE']='1'


def main():
    import test_browser_fixture as fixture
    import server
    import rule_pack_campaign as campaign
    from test_rule_pack_actors import ActorCampaignTests
    from waitress.server import create_server

    def preview_server(application,**options):
        example=ActorCampaignTests();example.setUp()
        state=campaign.execute_action(example.state,example.action,example.me)
        state=campaign.execute_action(state,example.action|{'actor':'b'*24,'npc':'sombra'},example.me)
        token=server.STORE.create('Vista local · PNJ y fichas privadas',campaign.initial_state({}),'Vista local')
        me=server.STORE.identity(token);cid=me['campaign']
        demo=campaign.import_campaign(state,me);row,_=server.STORE.campaigns[cid]
        server.STORE.campaigns[cid]=(row,server.STORE._light_state(cid,demo))

        def preview(environ,start_response):
            if environ.get('PATH_INFO') in ('/','/index.html'):
                html=(ROOT/'static/index.html').read_text(encoding='utf-8')
                html=html.replace('</head>','<script>localStorage.setItem("cronicas-token",'+json.dumps(token)+');</script></head>')
                banner='<aside style="padding:10px 18px;background:#243e39;color:#f3e4bd;text-align:center;font:14px sans-serif">Vista local · datos temporales de demostración · director simulado · sin servicios remotos</aside>'
                body=html.replace('<body>','<body>'+banner,1).encode('utf-8')
                start_response('200 OK',[('Content-Type','text/html; charset=utf-8'),('Content-Length',str(len(body))),('Cache-Control','no-store')])
                return [body]
            return application(environ,start_response)

        options.update(host='127.0.0.1',port=8765)
        return create_server(preview,**options)

    with patch('waitress.server.create_server',side_effect=preview_server):fixture.main()


if __name__=='__main__':main()
