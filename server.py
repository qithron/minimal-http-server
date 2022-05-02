#!/usr/bin/python
'''force to not exceed 79 chars

TODO: builtins.object HTTPServer :)
TODO:     threading need fix, use subprocess or threading?

TODO: add cache to reduce intensive modules, ex. generated files, etc ...
TODO: urusan logging mesti dibuat di thread lain, buat classnya sendiri
'''

import os
import io
import threading
import sys
import shutil
import time
import datetime
import email
import socketserver
import html
import urllib.parse
import http.client
#import logging # TODO: use logging or use fancy terminal color
from collections import namedtuple

try:
    from data import ENC, HTML_DOC
except ImportError:
    ENC = 'utf-8'
    HTML_DOC = b'<html><head><title>%s</title>%s</head><body>%s</body></html>'

_Request = namedtuple('RequestLine', ('method path version'),
    defaults=('HTTP/0.9',))

HTML_ERROR_TITLE= b'Error response'
HTML_ERROR_HEAD= b'<style>body{margin:1rem;}</style>'
HTML_ERROR_BODY= b'<h1>Error response</h1><hr><p>Error code: %d</p>' \
    b'<p>Message: %s</p><p>Error code explanation: %d - %s.</p><hr><p>%s</p>'

MIME = (
    'application/javascript ''js',
    'application/json '      'json',
    'image/bmp '             'bmp dib',
    'image/gif '             'gif',
    'image/jpeg '            'jpg jpeg jpe jfif',
    'image/png '             'png',
    'image/svg+xml '         'svg svgz',
    'image/vnd.microsoft.icon ico',
    'text/css '              'css',
    'text/html '             'html htm',
    'text/plain '            'txt sh text py pyw conf',
    'video/mp4 '             'mp4 mpg4 m4v mkv',
    'video/webm '            'webm',
)

def mime_parse():
    global MIME
    if type(MIME) == dict: return
    MIME = {ext: lst[0]
        for ent in MIME
        for lst in [ent.split()]
        for ext in lst[1:]}

def mime_types(path):
    basename = os.path.basename(path)
    if '.' in basename:
        ext = basename.rsplit('.',1)[1]
        if ext in MIME:
            return MIME[ext]
        ext = ext.lower()
        if ext in MIME:
            return MIME[ext]
    return 'application/octet-stream'

class STDIO:
    # TODO: buat sini logging vs terminal
    pass

class Compressor:
    # TODO: sekalian cek rasionya, jika no efek, masuk death note
    pass

class HTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    version_string = 'Python/%d.%d.%d' % sys.version_info[:3]

    def __init__(self, host, port, root, addon=None, bind_and_activate=True):
        '''add "extension" to handle class'''
        super().__init__((host, port), HTTPRequestHandler, bind_and_activate)
        self.root = os.path.normpath(root)
        self.addon_cls = addon
        self.addon_ins = tuple((a(self, root) for a in addon))

    allow_reuse_address = 1 # Seems to make sense in testing environment
    daemon_threads = True

    def server_bind(self):
        '''Override server_bind to store the server name.'''
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_port = port

###############################################################################

class HTTPRequestHandler:
    '''
    HTTP/0.9
    HTTP/1.0 https://datatracker.ietf.org/doc/html/rfc1945
    HTTP/1.1 https://datatracker.ietf.org/doc/html/rfc2616

    TODO: add HTTP/2.0 support

    TODO: check request request_headers, like opts:
    TODO:     Connection,conf Expect, Range, etc.
    TODO:     mk_header_parser to int, or something

    TODO: multiple range https://httpwg.org/specs/rfc7233.html#range.response

    TODO: FIXME: keep-alive, timeout

    TODO: FIXME: self.path_abs mungkin tidak konsisten
    '''

    #### constants
    code = http.HTTPStatus
    html_content_type = 'text/html; charset=' + ENC
    enc = 'utf-8'
    index_file = 'index.html', 'index.htm'

    HTTP_0_9_method = 'GET'
    HTTP_1_0_method = 'GET', 'HEAD', 'POST'
    HTTP_1_1_method = 'GET', 'HEAD', 'POST', \
        'CONNECT', 'DELETE', 'OPTIONS', 'PUT', 'TRACE'

    #### class vars
    rbufsize = -1
    wbufsize = 0
    timeout = 60
    nagle_algorithm = True

    #### instance vars
    # __init__
    connection = None # socket.socket
    address = None # (ip, port) client address
    server = None # ServerClass instance handler belong to
    root = None # server root dir
    addon = ()
    # setup
    rfile = None
    wfile = None
    # handle
    keep_alive = None
    url = None
    query = None
    path_rel = None # path in server
    path_abs = None # path in operating system
    request = None # namedtuple('method path version')
    request_headers = None # ro
    response_code = None # rw
    response_headers = None # rw
    response_index = None # marker for self.send_header()
    response_version = None # ro

    def __init__(self, request, address, server):
        self.connection = request
        self.address = address
        self.server = server

        self.root = server.root
        self.addon = server.addon_ins

        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def setup(self):
        if self.timeout is not None:
            self.connection.settimeout(self.timeout)
        if not self.nagle_algorithm:
            self.connection.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        if self.wbufsize == 0:
            self.wfile = socketserver._SocketWriter(self.connection)
        else:
            self.wfile = self.connection.makefile('wb', self.wbufsize)

    def handle(self):
        self.keep_alive = True
        while self.keep_alive:
            try:
                self.keep_alive = False
                self.response_index = 0
                self.response_headers = []
                line = self.rfile.readline(65537)
                if len(line) > 65536:
                    self.send_error(self.code.REQUEST_URI_TOO_LONG)
                elif line:
                    words = str(line, 'iso-8859-1').strip().split()
                    self.handle_next_step(words)
            except TimeoutError as err:
                self.keep_alive = False
                self.log_info('[HANDLE] %s', err)
            except ConnectionError as err:
                self.keep_alive = False
                self.log_warning('[HANDLE] %s', err)
            except Exception as err:
                self.keep_alive = False
                cls, ins, tra = sys.exc_info()
                while tra is not None:
                    self.log_warning('%s', tra.tb_frame)
                    tra = tra.tb_next if hasattr(tra, 'tb_next') else None
                self.log_error('[HANDLE] %s: %s', cls.__name__, err)
                self.send_error(self.code.INTERNAL_SERVER_ERROR,
                    '%s: %s' % (cls.__name__, err))

    def finish(self):
        if not self.wfile.closed:
            try:
                self.wfile.flush()
            except socket.error as err:
                self.log_warning('[FINISH] %s', err)
                # A final socket error may have occurred here, such as
                # the local error ECONNABORTED.
        self.wfile.close()
        self.rfile.close()

    #######################################################################

    def handle_next_step(self, words):
        # determine request version
        if len(words) == 2: # HTTP/0.9
            self.request = _Request(*words)
            if self.request.method != 'GET':
                self.send_error(self.code.BAD_REQUEST,
                    'Bad HTTP/0.9 request type (%s)' % request_method)
                return
            self.response_version = self.request.version
            self.url = urllib.parse.urlparse(self.request.path)
            self.path_abs = os.path.join(self.root,
                urllib.parse.unquote(self.url.path[1:]))
            self.HTTP_0_9()
            self.wfile.flush()
            return # HTTP/0.9 end here
        elif len(words) != 3:
            self.send_error(self.code.BAD_REQUEST,
                'Bad request syntax (%s)' % self.request)
            return

        # HTTP/1.x
        self.request = _Request(*words)
        match self.request.version: # check supported method
            case 'HTTP/1.0':
                if words[0] not in self.HTTP_1_0_method:
                    self.send_error(self.code.BAD_REQUEST,
                        'Unsupported method (%s) for request version %s'
                        % (self.request.method, self.request.version))
                    return
                self.response_method = self.HTTP_1_0
                self.response_version = self.request.version
            case 'HTTP/1.1':
                if words[0] not in self.HTTP_1_1_method:
                    self.send_error(self.code.BAD_REQUEST,
                        'Unsupported method (%s) for request version %s'
                        % (self.request.method, self.request.version))
                    return
                self.response_method = self.HTTP_1_1
                self.response_version = self.request.version
            case _:
                self.send_error(self.code.HTTP_VERSION_NOT_SUPPORTED,
                    'HTTP request version not supported (%s)'
                    % self.request.version)
                return

        # check real quick
        if not hasattr(self, 'do_' + self.request.method):
            self.send_error(self.code.NOT_IMPLEMENTED,
                'Not implemented (%s)' % self.request.method)
            return

        # request_headers
        try:
            self.request_headers = http.client.parse_headers(
                self.rfile, _class=http.client.HTTPMessage)
        except http.client.HTTPException as err:
            self.send_error(self.code.REQUEST_HEADER_FIELDS_TOO_LARGE,
                'Invalid request headers', str(err))
            return

        self.url = urllib.parse.urlparse(self.request.path)
        self.path_rel = os.path.normpath(urllib.parse.unquote(self.url.path))
        self.path_abs = os.path.normpath(self.root + self.path_rel)
        self.query = {}
        if self.url.query:
            for v in self.url.query.split('&'):
                self.query.setdefault(
                    *map(urllib.parse.unquote, v.lower().split('=', 1)))

        self.response_method()
        self.wfile.flush()

    #######################################################################

    def HTTP_0_9(self):
        basename = os.path.basename(self.path_abs)
        if '.' in basename:
            ext = basename.rsplit('.',1)[1]
            if ext == '.html' or ext == '.htm':
                if os.path.exists(self.path_abs):
                    with open(self.path_abs, 'rb') as f:
                        self.safe_write(f)
                    return
        self.safe_write(b'<html>404 not found</html>')

    def HTTP_1_0(self):
        getattr(self, 'do_' + self.request.method)()

    def HTTP_1_1(self):
        if self.request_headers.get('expect') == '100-continue':
            self.send_100()
            return
        if (self.timeout
        and self.request_headers.get('connection') == 'keep-alive'):
            self.keep_alive = True
            self.header_set('Keep-Alive',
                'timeout=%s, max=1000' % self.timeout)
            self.connection.settimeout(self.timeout)
        getattr(self, 'do_' + self.request.method)()

    #######################################################################
    # headers

    def header_response(self, code, message=None):
        self.response_code = code
        self.response_headers.insert(0,
            '%s %d %s' % (self.request.version, code, code.phrase))
        self.header_set('Server', self.server.version_string)
        self.header_set('Date', self.date_time_string())

    def header_set(self, keyword, value):
        self.response_headers.append('%s: %s' % (keyword, value))
        if keyword.lower() == 'connection':
            if value.lower() == 'close':
                self.keep_alive = False
            elif value.lower() == 'keep-alive':
                self.keep_alive = True

    def header_end(self):
        self.response_headers.append('\r\n')
        self.send_header()
        self.request_log(self.response_code)

    #######################################################################
    # logging

    def request_log(self, code, size='-'):
        if   code < 100: s = 'xxx'
        elif code < 200: s = '\033[1;37m%d\033[0m' % code # 1xx informational
        elif code < 300: s = '\033[1;32m%d\033[0m' % code # 2xx successful
        elif code < 400: s = '\033[1;33m%d\033[0m' % code # 3xx redirection
        elif code < 500: s = '\033[1;31m%d\033[0m' % code # 4xx client error
        elif code < 600: s = '\033[1;35m%d\033[0m' % code # 5xx server error
        else           : s = 'XXX'
        self.log('%s %s "%s"', s, str(size), ' '.join(self.request))

    def log(self, format, *args):
        sys.stdout.write('\033[1;37m[%s]\033[0m %s %s\n' % (
            time.strftime('%Y/%m/%d %H:%M:%S', time.localtime()),
            self.address[0], format%args))

    def log_info(self, format, *args):
        self.log('\033[1;37m%s\033[0m' % format, *args)

    def log_warning(self, format, *args):
        self.log('\033[1;33m%s\033[0m' % format, *args)

    def log_error(self, format, *args):
        self.log('\033[1;31m%s\033[0m' % format, *args)

    #######################################################################

    #_monthname = (None,
    #    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    #    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
    #def log(self, format, *args):
    #    year, month, day, hh, mm, ss, x, y, z = time.localtime()
    #    r = '%02d/%3s/%04d %02d:%02d:%02d' % (
    #        day, self._monthname[month], year, hh, mm, ss)
    #    s = self.address[0]
    #    sys.stderr.write('[%s] %s %s\n' % (r, s, format%args))

    def date_time_string(self, timestamp=None):
        """Return the current date and time formatted for a message header."""
        if timestamp is None:
            timestamp = time.time()
        return email.utils.formatdate(timestamp, usegmt=True)

    def redirect_path_equal(self, path):
        if path == self.request.path:
            return True
        self.send_301(path)
        return False

    #######################################################################

    def send_header(self):
        header = '\r\n'.join(self.response_headers[self.response_index:])
        self.safe_write(bytes(header, 'latin-1', 'strict'))
        self.response_index = len(self.response_headers)

    def send_100(self):
        # http.server.BaseHTTPRequestHandler.handle_expect_100
        self.response_code = 100
        self.response_headers.insert(0, self.request.version + ' 100')
        self.header_end()

    def send_301(self, new_location):
        '''MOVED_PERMANENTLY'''
        self.header_response(self.code.MOVED_PERMANENTLY)
        self.header_set('Location', new_location)
        self.header_set('Content-Length', '0')
        self.header_end()

    def send_307(self, new_location):
        '''TEMPORARY_REDIRECT'''
        self.header_response(self.code.TEMPORARY_REDIRECT)
        self.header_set('Location', new_location)
        self.header_set('Content-Length', '0')
        self.header_end()

    def send_304(self):
        '''NOT_MODIFIED
        try use web cache'''
        if ('If-Modified-Since' in self.request_headers
        and 'If-None-Match' not in self.request_headers):
            # compare If-Modified-Since and time of last file modification
            try:
                ims = email.utils.parsedate_to_datetime(
                    self.request_headers['If-Modified-Since'])
            except (TypeError, IndexError, OverflowError, ValueError):
                # ignore ill-formed values
                pass
            else:
                if ims.tzinfo is None:
                    # obsolete format with no timezone, cf.
                    # https://tools.ietf.org/html/rfc7231#section-7.1.1.1
                    ims = ims.replace(tzinfo=datetime.timezone.utc)
                if ims.tzinfo is datetime.timezone.utc:
                    # compare to UTC datetime of last modification
                    last_mod = datetime.datetime.fromtimestamp(
                        os.stat(self.path_abs).st_mtime, datetime.timezone.utc)
                    # remove microseconds, like in If-Modified-Since
                    last_mod = last_mod.replace(microsecond=0)
                    if last_mod <= ims:
                        self.header_response(self.code.NOT_MODIFIED)
                        self.header_end()
                        return True
        return False

    def send_file(self):
        if self.send_304():
            return
        content_type = mime_types(self.path_abs)
        stat = os.stat(self.path_abs)
        sz = stat.st_size
        mt = stat.st_mtime
        if self.request_headers.get('range'):
            s, e = self.request_headers.get('range')\
                       .split('=')[1].split('-')[:2]
            s = int(s)
            if e: e=int(e)
            else: e=sz-1
            self.header_response(self.code.PARTIAL_CONTENT)
            self.header_set('Content-Type', content_type)
            self.header_set('Content-Length', str(e-s+1))
            self.header_set('Content-Range', 'bytes %d-%d/%d' % (s, e, sz))
            self.header_set('Last-Modified', self.date_time_string(mt))
            self.header_end()
            if self.request.method == 'GET':
                with open(self.path_abs, 'rb') as f:
                    f.seek(s)
                    self.safe_write(f, length=e)
            return
        self.header_response(self.code.OK)
        self.header_set('Content-Type', content_type)
        self.header_set('Content-Length', str(sz))
        self.header_set('Last-Modified', self.date_time_string(mt))
        self.header_end()
        if self.request.method == 'GET':
            with open(self.path_abs, 'rb') as f:
                self.safe_write(f)

    def send_gen_html_file(self, doc, *headers):
        self.header_response(self.code.OK)
        self.header_set('Content-Type', self.html_content_type)
        self.header_set('Content-Length', str(len(doc)))
        for (n, v) in headers:
            self.header_set(n, v)
        self.header_end()
        if self.request.method == 'GET':
            self.safe_write(doc)

    def send_error(self, code, message=None, explain=None):
        stat = self.code(code)
        message = html.escape(stat.phrase if message is None else message)
        explain = html.escape(stat.description if explain is None else explain)
        self.header_response(code, message)
        self.header_set('Connection', 'close')
        # Message body is omitted for cases described in:
        #  - RFC7230: 3.3. 1xx, 204(No Content), 304(Not Modified)
        #  - RFC7231: 6.3.6. 205(Reset Content)
        if code >= 200 and code not in (204, 205, 304):
            server = html.escape(self.server.version_string)
            f = lambda obj: obj.encode(ENC) if type(obj) == str else obj
            t = tuple(map(f, (code, message, code, explain, server)))
            title = HTML_ERROR_TITLE
            head = HTML_ERROR_HEAD
            body = HTML_ERROR_BODY % t
            doc = HTML_DOC % (title, head, body)
            self.header_set('Content-Type', 'text/html;charset=utf-8')
            self.header_set('Content-Length', str(len(doc)))
            self.header_end()
            if self.request.method != 'HEAD':
                self.safe_write(doc)
        else:
            self.header_end()

    #######################################################################

    def safe_read(self, length, fsrc=None):
        if fsrc is None:
            fsrc = self.rfile
        return fsrc.read(length)

    def safe_write(self, fsrc, fdst=None, length=None):
        s = io.BytesIO(fsrc) if type(fsrc) == bytes else fsrc
        d = self.wfile if fdst is None else fdst
        shutil.copyfileobj(s, d, length)
        return True

    #######################################################################

    def addon_rule(self):
        for addon in self.addon:
            if addon.rule(self):
                return True
        return False

    def do_GET(self):
        '''redirect to self.do_GET_HEAD'''
        self.do_GET_HEAD()

    def do_HEAD(self):
        '''redirect to self.do_GET_HEAD'''
        self.do_GET_HEAD()

    def do_GET_HEAD(self):
        if self.addon_rule():
            pass
        elif self.path_abs == self.root:
            if self.is_path_exact('/'):
                for fn in self.index_file:
                    rp = os.path.join(self.path_abs, fn)
                    if os.path.exists(rp):
                        self.path_abs = rp
                        self.send_file()
                        break
                else:
                    self.send_error(self.code.FORBIDDEN)
        elif os.path.isfile(self.path_abs):
            self.send_file()
        elif os.path.isdir(self.path_abs):
            self.send_error(self.code.FORBIDDEN)
        else:
            self.send_error(self.code.NOT_FOUND)

    def do_POST(self):
        if self.addon_rule():
            pass
        else:
            self.send_error(self.code.BAD_REQUEST)

def _run(host, port, root):
    try:
        lst = [f[:-3] for f in os.listdir(os.path.join(root, 'data'))
            if not f.startswith('_') and f.endswith('.py')]
        data = __import__('data', fromlist=lst)
        addon = [getattr(getattr(data, n), n) for n in lst]
        addon.sort(reverse=True, key=lambda x: x.priority)
    except Exception as err: # run in basic mode
        cls, ins, tra = sys.exc_info()
        while tra is not None:
            print(tra.tb_frame)
            tra = tra.tb_next if hasattr(tra, 'tb_next') else None
        if cls == AttributeError:
            raise SystemExit
        print('\033[1;31m%s\033[0m' % err)
        print('running in basic mode, no addon being used')
        addon = ()
    return HTTPServer(host, port, root, addon, HTTPRequestHandler)

if __name__ == '__main__':
    mime_parse()
    from threading import Thread
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--background', action='store_false',
        help='Background mode')
    parser.add_argument('-n', '--host', default='0.0.0.0',
        help='Start an HTTP server with the given host (default: 0.0.0.0)')
    parser.add_argument('-p', '--port', default=80, type=int,
        help='Start an HTTP server on the given port (default: 80)')
    parser.add_argument('-r', '--root', default=os.path.dirname(__file__),
        help='Server root directory (default: <script current directory>)')
    args = parser.parse_args()

    httpd = _run(args.host, args.port, args.root)
    srvcd = Thread(target=httpd.serve_forever)
    srvcd.start()
    print('Server ready at http://%s:%d/' % httpd.server_address)
    if args.background:
        while True:
            print('Server commands: [q]uit')
            if input() == 'q':
                break
        httpd.shutdown()
    srvcd.join()
    print('Server stopped')
