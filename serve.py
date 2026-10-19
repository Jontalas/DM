"""Servidor de producción, un proceso con varios hilos para conservar LOCK."""
import os
import server
from wsgi import application


def main():
    server.initialize()
    from waitress import serve
    host=os.environ.get('HOST','0.0.0.0')
    port=int(os.environ.get('PORT','8787'))
    print(f'Crónicas: servidor de producción en {host}:{port}',flush=True)
    serve(application,host=host,port=port,threads=16,channel_timeout=240,max_request_body_size=8_000_000)


if __name__=='__main__': main()
