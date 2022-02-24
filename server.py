'''force to not exceed 79 chars

TODO: add cache to reduce intensive modules, ex. generated files, etc ...

TODO: override error page
TODO: override error page (2)
TODO: override error page (3)
TODO: override error page (4)
TODO: override error page (5)
TODO: override error page (6)
TODO: override error page (7)
TODO: override error page (8)
TODO: override error page (9)
'''

import os
import io
import threading
import sys
import shutil
import time
import datetime
import email
import urllib.parse
import socket
import socketserver
import html
import http.client

conf = '%(script_path)s/data/server.conf'
__version__ = '0.1'

class Addon:
    '''template for "sub RequestHandlerClass", (like: listdir, POST request)
    without any "sub RequestHandlerClass", server only accept file requests,
    and request to directories is FORBIDDEN'''

    def __init__(self, server, root):
        pass

    def rule(self, this):
        return False

class CustomHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, conf, addon=None, /, *args, **kwargs):
        '''add "extension" to handle class'''
        super().__init__(*args, **kwargs)
        self.RequestHandlerClass.root = conf.root
        self.RequestHandlerClass.mime = conf.mime
        if addon:
            self.RequestHandlerClass.addon = [a(self,conf.root) for a in addon]

    allow_reuse_address = 1 # Seems to make sense in testing environment
    daemon_threads = True

    def server_bind(self):
        '''Override server_bind to store the server name.'''
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port

###############################################################################
###############################################################################
###############################################################################

_print = lambda *args: print('\033[1;33m%s\033[0m %s' % args)

class CustomHTTPRequestHandler(socketserver.StreamRequestHandler):
    '''
    HTTP/0.9
    HTTP/1.0 https://datatracker.ietf.org/doc/html/rfc1945
    HTTP/1.1 https://datatracker.ietf.org/doc/html/rfc2616

    TODO: add self.path correction, self.redirect_permanent, misal, hapus query

    TODO: add HTTP/2.0 support

    TODO: make backup for response header, self.send_header()

    TODO: check request headers, like opts: Connection, Expect, Range, etc.
    TODO:     mk_header_parser to int, or something

    TODO: multiple range https://httpwg.org/specs/rfc7233.html#range.response
    '''

    html_error = ('<!doctype html><html><head>'
        '<meta http-equiv="Content-Type" content="text/html;charset=utf-8">'
        '<title>Error response</title>'
        '</head>'
        '<body>'
            '<h1>Error response</h1>'
            '<p>Error code: %(code)d</p>'
            '<p>Message: %(message)s.</p>'
            '<p>Error code explanation: %(code)s - %(explain)s.</p>'
        '</body></html>')

    server_version = 'MantapMantap/' + __version__
    sys_version = 'Python/' + sys.version.split(maxsplit=1)[0]

    # constant from socketserver.StreamRequestHandler
    rbufsize = -1
    wbufsize = 0
    timeout = 5
    disable_nagle_algorithm = False
    # constant
    enc = 'utf-8'
    root = '/srv/http'
    mime = None
    code = http.HTTPStatus
    addon = []
    close_connection = True

    # instance var from socketserver.BaseRequestHandler
    request = None # socket.socket
    client_address = None # ('127.0.0.1', 36618)
    server = None # ServerClass
    # instance var from socketserver.StreamRequestHandler
    connection = None # = self.request
    rfile = None
    wfile = None
    # instance var, sorted
    raw_requestline = None
    requestline = None
    request_version = None
    protocol_version = None
    command = None # request method
    path = None # url
    path_abs = None # root + path
    headers = None # request headers
    headerr = None # response headers
    query = None # url payload

    def handle(self):
        self.handle_one_request()
        while not self.close_connection:
            self.handle_one_request()

    def handle_one_request(self):
        try:
            self.headerr = []
            self.raw_requestline = self.rfile.readline(65537)
            if not self.raw_requestline:
                self.close_connection = True
            elif len(self.raw_requestline) > 65536:
                self.send_error(self.code.REQUEST_URI_TOO_LONG)
            elif self.handle_one_request_ex():
                self.wfile.flush()
        except TimeoutError as err:
            self.log('%s', err)
            self.close_connection = True
        except ConnectionResetError as err:
            self.log('%s', err)
            self.close_connection = True

    def handle_one_request_ex(self):
        self.close_connection = True
        self.requestline = str(self.raw_requestline, 'iso-8859-1').strip()
        words = self.requestline.split()
        # determine request version
        if len(words) == 2: # HTTP/0.9
            if words[0] != 'GET':
                self.send_error(self.code.BAD_REQUEST,
                    'Bad HTTP/0.9 request type (%s)' % command)
                return False
            self.request_version = self.protocol_version = 'HTTP/0.9'
            self.command, self.path = words
            self.path_abs = os.path.join(self.root, urllib.parse.unquote(
                urllib.parse.urlsplit(self.path).path[1:]))
            self.HTTP_0_9()
            return True # HTTP/0.9 end here
        elif len(words) != 3:
            self.send_error(self.code.BAD_REQUEST,
                'Bad request syntax (%s)' % self.requestline)
            return False
        match words[2]: # newer
            case 'HTTP/1.0':
                self.request_version = self.protocol_version = 'HTTP/1.0'
            case 'HTTP/1.1':
                self.request_version = self.protocol_version = 'HTTP/1.1'
            case _:
                self.send_error(self.code.HTTP_VERSION_NOT_SUPPORTED,
                    'HTTP request version not supported (%s)' % words[3])
                return False
        # check supported method
        match self.request_version:
            case 'HTTP/1.0':
                if words[0] not in ('GET', 'HEAD', 'POST'):
                    self.send_error(self.code.BAD_REQUEST,
                        'Unsupported method (%s) for request version %s' %
                        (self.command, self.request_version))
                    return False
            case 'HTTP/1.1':
                if words[0] not in (
                    'CONNECT', 'DELETE', 'GET', 'HEAD',
                    'OPTIONS', 'POST', 'PUT', 'TRACE'):
                    self.send_error(self.code.BAD_REQUEST,
                        'Unsupported method (%s) for request version %s' %
                        (self.command, self.request_version))
                    return False
                pass
        # check real quick
        self.command, self.path = words[:2]
        if not hasattr(self, 'do_'+self.command):
            self.send_error(self.code.NOT_IMPLEMENTED,
                'Not implemented (%s)' % self.command)
            return False
        # headers
        try:
            self.headers = http.client.parse_headers(
                self.rfile, _class=http.client.HTTPMessage)
        except http.client.LineTooLong as err:
            self.send_error(self.code.REQUEST_HEADER_FIELDS_TOO_LARGE,
                'Line too long', str(err))
            return False
        except http.client.HTTPException as err:
            self.send_error(self.code.REQUEST_HEADER_FIELDS_TOO_LARGE,
                'Too many headers', str(err))
            return False
        # query
        query = urllib.parse.urlsplit(self.path).query
        if '=' in query:
            self.query = {p[0]: p[1] for o in query.split('&') if '=' in o
                for p in [[*map(urllib.parse.unquote, o.split('='))]]}
        # path_abs
        self.path_abs = os.path.join(self.root,
            urllib.parse.unquote(urllib.parse.urlsplit(self.path).path[1:]))
        # finally
        match self.request_version:
            case 'HTTP/1.0':
                self.HTTP_1_0()
            case 'HTTP/1.1':
                self.HTTP_1_1()
        return True

    def HTTP_0_9(self):
        basename = os.path.basename(self.path_abs)
        if basename.count('.'):
            ext = basename.rsplit('.',1)[1]
            if ext == '.html' or ext == '.htm':
                if os.path.exists(self.path_abs):
                    with open(self.path_abs, 'rb') as f:
                        self.safe_write(f)
                    return
        self.safe_write(b'<html>forofor: not found</html>')

    def HTTP_1_0(self):
        getattr(self, 'do_' + self.command)()

    def HTTP_1_1(self):
        if self.headers.get('expect') == '100-continue':
            if not self.expect_100_continue():
                return
        if self.headers.get('connection') == 'keep-alive' and self.timeout:
            self.close_connection = False
            self.header_set('Keep-Alive', f'timeout={self.timeout}, max=1000')
            self.connection.settimeout(self.timeout)
        getattr(self, 'do_' + self.command)()

    def expect_100_continue(self):
        '''for future

        http.server.BaseHTTPRequestHandler.handle_expect_100
        '''
        self.safe_write('%s %d\r\n\r\n' %
            (self.protocol_version, 100).encode('latin-1', 'strict'))
        return True

    def redirect_permanent(self, new_url):
        self.header_response(self.code.MOVED_PERMANENTLY)
        self.header_set('Location', new_url)
        self.header_set('Content-Length', '0')
        self.header_end()

    def send_error(self, code, message=None, explain=None):
        status = self.code(code)
        if message is None:
            message = status.phrase
        if explain is None:
            explain = status.description
        self.header_response(code, message)
        self.header_set('Connection', 'close')
        # Message body is omitted for cases described in:
        #  - RFC7230: 3.3. 1xx, 204(No Content), 304(Not Modified)
        #  - RFC7231: 6.3.6. 205(Reset Content)
        if code >= 200 and code not in (204, 205, 304):
            body = (self.html_error % {
                'code': code,
                'message': html.escape(message, quote=False),
                'explain': html.escape(explain, quote=False)}
            ).encode('utf-8', 'replace')
            self.header_set('Content-Type', 'text/html;charset=utf-8')
            self.header_set('Content-Length', str(len(body)))
            self.header_end()
            if self.command != 'HEAD':
                self.safe_write(body)
        else:
            self.header_end()

    def send_header(self):
        self.safe_write('\r\n'.join(self.headerr).encode('latin-1','strict')) \
        and self.headerr.clear()

    def header_response(self, code, message=None):
        self.request_log(code)
        self.headerr.insert(0, f'{self.request_version} {code} {code.phrase}')
        self.header_set('Server', self.version_string())
        self.header_set('Date', self.date_time_string())

    def header_set(self, keyword, value):
        self.headerr.append('%s: %s' % (keyword, value))
        if keyword.lower() == 'connection':
            if value.lower() == 'close':
                self.close_connection = True
            elif value.lower() == 'keep-alive':
                self.close_connection = False

    def header_end(self):
        self.headerr.append('\r\n')
        self.send_header()

    def request_log(self, code, size='-'):
        if code < 200: # 1xx informational
            s = f'\033[1;37m{code}\033[0m'
        elif code < 300: # 2xx successful
            s = f'\033[1;32m{code}\033[0m'
        elif code < 400: # 3xx redirection
            s = f'\033[1;33m{code}\033[0m'
        elif code < 500: # 4xx client error
            s = f'\033[1;31m{code}\033[0m'
        elif code < 600: # 5xx server error
            s = f'\033[1;35m{code}\033[0m'
        else:
            s = 'xxx'
        self.log('%s %s "%s"', s, str(size), self.requestline)

    def log(self, format, *args):
        sys.stderr.write('[%s] %s %s\n' % (
            time.strftime('%Y/%m/%d %H:%M:%S', time.localtime()),
            self.client_address[0], format%args))

    _monthname = (None,
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
    def log2(self, format, *args):
        year, month, day, hh, mm, ss, x, y, z = time.localtime()
        r = '%02d/%3s/%04d %02d:%02d:%02d' % (
            day, self._monthname[month], year, hh, mm, ss)
        s = self.client_address[0]
        sys.stderr.write('[%s] %s %s\n' % (r, s, format%args))

    def log_warning(self, format, *args):
        self.log('\033[1;33m%s\033[0m' % format, *args)

    def log_error(self, format, *args):
        self.log('\033[1;31m%s\033[0m' % format, *args)

    def version_string(self):
        """Return the server software version string."""
        return self.server_version + ' ' + self.sys_version

    def date_time_string(self, timestamp=None):
        """Return the current date and time formatted for a message header."""
        if timestamp is None:
            timestamp = time.time()
        return email.utils.formatdate(timestamp, usegmt=True)

    def safe_write(self, fsrc, fdst=None, length=None):
        '''
        safe write to client
        return True on success, False otherwise
        accept file object and bytes
        '''
        s = io.BytesIO(fsrc) if type(fsrc) == bytes else fsrc
        d = self.wfile if fdst is None else fdst
        try:
            shutil.copyfileobj(s, d, length)
            return True
        except (BrokenPipeError, ConnectionResetError) as e:
            self.log_error('%s', e)
            return False

    def safe_read(self, length, fsrc=None):
        if not fsrc:
            fsrc = self.rfile
        try:
            return fsrc.read(length)
        except (BrokenPipeError, ConnectionResetError) as e:
            self.log_error('%s', e)
            return False

    def mime_types(self):
        basename = os.path.basename(self.path_abs)
        if basename.count('.'):
            ext = basename.rsplit('.',1)[1]
        else:
            return 'application/octet-stream'
        if ext in self.mime:
            return self.mime[ext]
        ext = ext.lower()
        if ext in self.mime:
            return self.mime[ext]
        return 'application/octet-stream'

    def send_file(self):
        if self.use_cache():
            return
        content_type = self.mime_types()
        stat = os.stat(self.path_abs)
        sz = stat.st_size
        mt = stat.st_mtime
        if self.headers.get('range'):
            s, e = self.headers.get('range').split('=')[1].split('-')
            s = int(s)
            if e: e=int(e)
            else: e=sz-1
            self.header_response(self.code.PARTIAL_CONTENT)
            self.header_set('Content-type', content_type)
            self.header_set('Content-Length', str(e-s+1))
            self.header_set('Content-Range', f'bytes {s}-{e}/{sz}')
            self.header_set('Last-Modified', self.date_time_string(mt))
            self.header_end()
            if self.command == 'GET':
                with open(self.path_abs, 'rb') as f:
                    f.seek(s)
                    self.safe_write(f, length=e)
            return
        self.header_response(self.code.OK)
        self.header_set('Content-type', content_type)
        self.header_set('Content-Length', str(sz))
        self.header_set('Last-Modified', self.date_time_string(mt))
        self.header_end()
        if self.command == 'GET':
            with open(self.path_abs, 'rb') as f:
                self.safe_write(f)
        return

    def use_cache(self):
        if ('If-Modified-Since' in self.headers
        and 'If-None-Match' not in self.headers):
            # compare If-Modified-Since and time of last file modification
            try:
                ims = email.utils.parsedate_to_datetime(
                    self.headers['If-Modified-Since'])
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

    def call_addon_rule(self):
        for addon in self.addon:
            if addon.rule(self):
                break
        else:
            return False
        return True

    def do_GET(self):
        '''redirect to self.do_GET_HEAD'''
        self.do_GET_HEAD()

    def do_HEAD(self):
        '''redirect to self.do_GET_HEAD'''
        self.do_GET_HEAD()

    def do_GET_HEAD(self):
        if self.call_addon_rule():
            pass
        elif os.path.isfile(self.path_abs):
            self.send_file()
        elif os.path.isdir(self.path_abs) or os.path.islink(self.path_abs):
            self.send_error(self.code.FORBIDDEN)
        else:
            self.send_error(self.code.NOT_FOUND)

    def do_POST(self):
        if self.call_addon_rule():
            pass
        else:
            self.send_error(self.code.BAD_REQUEST)

def _run(conf=conf):
    script_path = os.path.dirname(__file__)
    conf = conf % {'script_path': script_path}
    with open(conf) as t:
        conf = type('conf', (), eval(t.read()))
    conf.root = os.path.normpath(conf.root)
    conf.mime = {ext: lst[0]
        for ent in conf.mime
        for lst in [ent.split()]
        for ext in lst[1:]}
    from data import \
        serverinfo, \
        freechat, \
        pydoc, \
        python_regex_tester, \
        listdir
    addon = (
        serverinfo.serverinfo,
        freechat.freechat,
        pydoc.pydoc,
        python_regex_tester.python_regex_tester,
        listdir.listdir,) # last, because it's ignore the query
    return CustomHTTPServer(conf, addon,
        (conf.addr,conf.port), CustomHTTPRequestHandler)

if __name__ == '__main__':
    from threading import Thread
    httpd = _run()
    srvcd = Thread(target=httpd.serve_forever)
    srvcd.start()
    print('Server ready at http://%s:%d/' % httpd.server_address)
    try:
        while True:
            print('Server commands: [q]uit')
            match input():
                case 'q':
                    httpd.shutdown()
                    break
    except KeyboardInterrupt:
        httpd.shutdown()
        print()
    srvcd.join()
    print('Server stopped')
