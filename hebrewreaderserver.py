#!/usr/bin/env python3
from contextlib import contextmanager
from http.server import HTTPServer, HTTPStatus, BaseHTTPRequestHandler
import os
import re
from shutil import copyfileobj
import signal
import tempfile
from urllib.parse import urlparse, parse_qs

from tf.fabric import Fabric
from hebrewreader import generate, load_verse_nodes

TEMPLATES = {}

# https://stackoverflow.com/a/601168/1544337
class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException('Timed out!')
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

class HTTPRequestHandler(BaseHTTPRequestHandler):
    def send_quick_response(self, status, message):
        self.send_response(status, message)
        self.end_headers()
        self.wfile.write(bytes(message, 'utf-8'))

    def do_GET(self):
        req = urlparse('http://localhost' + self.path)
        if req.path == '/':
            self.do_send_file('index.html')
        elif req.path == '/reader':
            self.do_generate_reader(**parse_qs(req.query, keep_blank_values=True))
        elif re.match(r'^\/\.well-known\/acme-challenge\/\w*$', req.path) and \
                os.path.isfile(req.path[1:]):
            self.do_send_file(req.path[1:])
        else:
            self.send_quick_response(HTTPStatus.NOT_FOUND, 'Not found')

    def do_send_file(self, fname):
        self.send_response(HTTPStatus.OK, 'OK')
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        with open(fname, 'rb') as f:
            copyfileobj(f, self.wfile)

    def do_generate_reader(self, fmt=['pdf'], include_voca=None, combine_voca=None, passages=None, **kwargs):
        if passages is None or len(passages) == 0:
            self.send_quick_response(HTTPStatus.BAD_REQUEST, 'No passages given')
            return
        passages = [p.strip() for ps in passages for p in ps.split('\n')]
        fmt = fmt[-1]
        if fmt != 'pdf' and fmt != 'tex':
            self.send_quick_response(HTTPStatus.BAD_REQUEST, 'Unknown format')
            return

        tex = tempfile.mkstemp(suffix='.tex', prefix='reader')
        tex = open(tex[1], 'w', encoding='utf-8')
        pdf = tempfile.mkstemp(suffix='.pdf', prefix='reader')[1]

        try:
            with time_limit(5):
                generate(passages,
                        include_voca is not None and include_voca,
                        combine_voca is not None and combine_voca,
                        tex, None if fmt == 'tex' else pdf,
                        TEMPLATES, quiet=True)
        except TimeoutException as e:
            self.send_quick_response(HTTPStatus.REQUEST_TIMEOUT, str(e))
            return
        except Exception as e:
            self.send_quick_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
            return

        output = tex.name if fmt == 'tex' else pdf
        content_type = 'application/x-latex' if fmt == 'tex' else 'application/pdf'
        filename = 'reader.' + fmt
        with open(output, 'rb') as f:
            self.send_response(HTTPStatus.OK, 'OK')
            self.send_header('Content-Type', '{}; charset=utf-8'.format(content_type))
            self.send_header('Content-Disposition', 'attachment; filename={}'.format(filename))
            self.end_headers()
            copyfileobj(f, self.wfile)
            return

        self.send_quick_response(HTTPStatus.NOT_FOUND, 'Not found')

def main():
    TEMPLATES['pre'] = open('pre.tex', encoding='utf-8').read()
    TEMPLATES['post'] = open('post.tex', encoding='utf-8').read()
    TEMPLATES['pretext'] = open('pretext.tex', encoding='utf-8').read()
    TEMPLATES['posttext'] = open('posttext.tex', encoding='utf-8').read()
    TEMPLATES['prevoca'] = open('prevoca.tex', encoding='utf-8').read()
    TEMPLATES['postvoca'] = open('postvoca.tex', encoding='utf-8').read()

    load_verse_nodes()

    print('Listening on port 19419...')
    address = ('', 19419)
    httpd = HTTPServer(address, HTTPRequestHandler)
    httpd.serve_forever()

if __name__ == '__main__':
    main()
