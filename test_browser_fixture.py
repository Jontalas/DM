"""Servidor desechable SOLO para Playwright, sin credenciales ni servicios remotos."""
import os
import engine
import server
from test_support import TestStore
from wsgi import application


def main():
    from waitress.server import create_server
    os.environ.pop('ANTHROPIC_API_KEY',None)
    os.environ.pop('FIREBASE_STORAGE_BUCKET',None)
    server.STORE=TestStore()
    # Predictable dice only inside this explicitly isolated test process.
    engine.secrets.randbelow=lambda sides:min(11,sides-1)
    http=create_server(application,host='127.0.0.1',port=0,threads=4)
    print('http://127.0.0.1:'+str(http.effective_port),flush=True)
    http.run()


if __name__=='__main__':main()
