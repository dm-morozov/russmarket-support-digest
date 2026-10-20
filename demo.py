"""Build and preview the same static artifact as GitHub Pages; loopback only."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from scripts.build_pages import build


class StaticHandler(SimpleHTTPRequestHandler):
    def log_message(self,format,*args):pass


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    folder=build()
    with ThreadingHTTPServer(('127.0.0.1',args.port),partial(StaticHandler,directory=str(folder))) as server:
        print(f'Preview: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
