#!/usr/bin/env python3
from argparse import ArgumentParser
from contextlib import contextmanager
import gc
from http.server import HTTPServer, HTTPStatus, BaseHTTPRequestHandler
from shutil import copyfileobj
import signal
import tempfile
from urllib.parse import urlparse, parse_qs

from tf.fabric import Fabric
from hebrewreader import generate, load_data

LOCATION = {}
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
            self.do_send_index()
        elif req.path == '/reader':
            self.do_generate_reader(**parse_qs(req.query, keep_blank_values=True))
        else:
            self.send_quick_response(HTTPStatus.NOT_FOUND, 'Not found')

    def do_send_index(self):
        self.send_response(HTTPStatus.OK, 'OK')
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        with open('index.html', 'rb') as f:
            copyfileobj(f, self.wfile)

    def do_generate_reader(self, fmt=['pdf'], combine_voca=None, passages=None, **kwargs):
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
            api = load_data(LOCATION['bhsa'], LOCATION['module'])
            with time_limit(5):
                generate(passages, combine_voca is not None,
                        tex, None if fmt == 'tex' else pdf,
                        TEMPLATES, api, quiet=True)
            del api
            gc.collect()
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
    parser = ArgumentParser(description='HTTP server for hebrew-reader')

    p_data = parser.add_argument_group('Data source options')
    p_data.add_argument('--bhsa', '-b', nargs=1, required=True,
            help='Location of the BHSA data')
    p_data.add_argument('--module', '-m', nargs=1, required=True,
            help='Text-fabric module to load')

    args = parser.parse_args()

    LOCATION['bhsa'] = args.bhsa
    LOCATION['module'] = args.module

    TEMPLATES['pre'] = open('pre.tex', encoding='utf-8').read()
    TEMPLATES['post'] = open('post.tex', encoding='utf-8').read()
    TEMPLATES['pretext'] = open('pretext.tex', encoding='utf-8').read()
    TEMPLATES['posttext'] = open('posttext.tex', encoding='utf-8').read()
    TEMPLATES['prevoca'] = open('prevoca.tex', encoding='utf-8').read()
    TEMPLATES['postvoca'] = open('postvoca.tex', encoding='utf-8').read()

    print('Listening on port 19419...')
    address = ('', 19419)
    httpd = HTTPServer(address, HTTPRequestHandler)
    httpd.serve_forever()

if __name__ == '__main__':
    main()
