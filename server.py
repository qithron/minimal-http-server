#!/bin/python

'''
https://choosealicense.com/licenses/mit/
'''

import os
import time
import shutil
import html
import posixpath
import email
import datetime
import re
import urllib.parse

from threading import Thread
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler

cfg = {
    'port': 80,
    'root': '/mnt/home/qtr/pub/www', # do not end with slash
    'mime': ( # WARNING: seperator exactly 1 space only
        'application/javascript'' js',
        'image/bmp'             ' bmp dib',
        'image/gif'             ' gif',
        'image/jpeg'            ' jpg jpeg jpe jfif',
        'image/png'             ' png',
        'image/svg+xml'         ' svg svgz',
        'image/vnd.microsoft.icon ico',
        'text/css'              ' css',
        'text/html'             ' html html',
        'text/plain'            ' txt sh text py pyw',
        'video/mp4'             ' mp4 mpg4 m4v mkv',
        'video/webm'            ' webm',
        #video/x-matroska mkv;
    ),
}

# def unhumanhtml(s):
#     '''Strip HTML files to single line.'''
#     re.sub("(<!--.*?-->)", "", s, flags=re.DOTALL)

def humanfilesize(size, sys=tuple('KMGTP')):
    '''$ ls --human-readable'''
    if size < 1024:
        return str(size)
    else:
        step = -1
        while size >= 1024:
            step += 1
            size /= 1024
        s, f = str(round(size, 2)).split('.')
        return f'{s}.{f if len(f) == 2 else f"{f}0"}{sys[step]}'

def server_uptime(start_time):
    '''$ uptime'''
    d = int(time.time()) - start_time
    t = []
    if d >= 86400:
        i, d = divmod(d, 86400)
        t.append(f'{i} days, ')
    else:
        t.append('0 days, ')
    if d >= 3600:
        i, d = divmod(d, 3600)
        t.append(f'{i:02d}.')
    else:
        t.append('00.')
    if d >= 60:
        i, d = divmod(d, 60)
        t.append(f'{i:02d}.')
    else:
        t.append('00.')
    t.append(f'{d:02d}')
    return ''.join(t)

def use_cache(self, realpath):
    '''Use cache if possible.'''
    if ("If-Modified-Since" in self.headers
            and "If-None-Match" not in self.headers):
        # compare If-Modified-Since and time of last file modification
        try:
            ims = email.utils.parsedate_to_datetime(
                self.headers["If-Modified-Since"])
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
                    os.stat(realpath).st_mtime, datetime.timezone.utc)
                # remove microseconds, like in If-Modified-Since
                last_mod = last_mod.replace(microsecond=0)
                if last_mod <= ims:
                    self.send_response(HTTPStatus.NOT_MODIFIED)
                    self.end_headers()
                    return True
    return False

def HTML_raw_file(self, realpath, request_method):
    '''Send raw file.'''
    st = os.stat(realpath)
    if use_cache(self, realpath):
        return None
    content_type = self.guess_type(realpath)
    self.send_response(HTTPStatus.OK)
    self.send_header("Content-type", content_type)
    self.send_header("Content-Length", str(st[6]))
    self.send_header("Last-Modified", self.date_time_string(st.st_mtime))
    self.end_headers()
    if request_method == 'GET':
        with open(realpath, 'rb') as f:
            shutil.copyfileobj(f, self.wfile)
    return None

def HTML_list_directory(self, realpath, request_method):
    '''
    Generate HTML document for Directory listing:
        - GNU "ls -la" style
        - case insensitive
        - folder first
        - broken links
    '''
    try:
        if use_cache(self, (realpath)):
            return None
        lst = sorted(os.listdir(realpath),key=lambda a: a.lower())
    except OSError:
        self.send_error(
            HTTPStatus.NOT_FOUND, 'No permission to list directory')
        return None
    # top bar for navigation
    dirs = [v for v in realpath.removeprefix(cfg['root']).split('/') if v]
    dirs.reverse()
    a = [f'''<a href="{('../' * (len(dirs) if dirs else 1))}?">'''
        '<span style="color:#ff0000;font-style:italic;font-weight:bold;">'
        'root</span>/</a>'
    ]
    for i in range(len(dirs)-1, -1, -1):
        a.append(f'''<a href="{('../'*i)}">{dirs[i]}/</a>''')
    navbar = '<table id=navbar><tr><td>' + ''.join(a) + '</td></tr></table>'
    # total items
    info = f'<span>total: {len(lst)} item(s)</span>'
    # entries, including . and ..
    d = [] # directories
    e = [] # files
    b = [] # broken links
    for fn in '.', '..':
        fullpath = f'{realpath}/{fn}'
        st = os.stat(fullpath)
        sm = (os.path.samefile(cfg['root'], fullpath)
            or fullpath == cfg['root'] + '/..')
        name = fn
        link = fn + ('/?' if sm else '/')
        date = time.strftime('%Y-%b-%d %H:%M:%S',time.gmtime(st.st_ctime))
        d.append('<tr>'
            f'<td class="name">'
                f'<a href="{link}"><div>{name}/</div></a></td>'
            f'<td class="date">{date}</td>'
            f'<td class="size">-</td>'
            f'<td class="size">-</td>'
            f'<td class="icon"><a href="{link}">🖿</a></td>'
        '</tr>')
    for fn in lst:
        fullpath = f'{realpath}/{fn}'
        exists = os.path.exists(fullpath)
        st = os.stat(fullpath, follow_symlinks=exists)
        name = html.escape(fn, quote=False)
        link = urllib.parse.quote(fn)
        date = time.strftime('%Y-%b-%d %H:%M:%S',time.gmtime(st.st_ctime))
        if not exists:
            size = st.st_size
            hsze = humanfilesize(size)
            b.append('<tr>'
                f'<td class="name">{name}</td>'
                f'<td class="date">{date}</td>'
                f'<td class="size">{size}</td>'
                f'<td class="size">{hsze}</td>'
                f'<td class="icon">!</td>'
            '</tr>')
        elif os.path.isdir(fullpath):
            d.append('<tr>'
                f'<td class="name">'
                    f'<a href="{link}/"><div>{name}/</div></a></td>'
                f'<td class="date">{date}</td>'
                f'<td class="size">-</td>'
                f'<td class="size">-</td>'
                f'<td class="icon"><a href="{link}/">🖿</a></td>'
            '</tr>')
        else:
            size = st.st_size
            hsze = humanfilesize(size)
            e.append('<tr>'
                f'<td class="name">'
                    f'<a href="{link}"><div>{name}</div></a></td>'
                f'<td class="date">{date}</td>'
                f'<td class="size">{size}</td>'
                f'<td class="size">{hsze}</td>'
                f'<td class="icon">'
                    f'<a href="{link}" download="{name}">🠋</a></td>'
            '</tr>')
    head, foot = map(
        lambda s: bytes(s, encoding='utf-8'),
        open('listdir.html').read().replace('\n','').split('<!---->'))
    doc = (head +
        bytes(navbar, encoding='utf-8') +
        bytes(info, encoding='utf-8') +
        b'<table id="lstdir">' +
        ''.join(d).encode('utf-8') +
        ''.join(e).encode('utf-8') +
        ''.join(b).encode('utf-8') +
        b'</table>' + foot
    )
    self.send_response(HTTPStatus.OK)
    self.send_header('Content-type', 'text/html; charset=utf-8')
    self.send_header('Content-Length', str(len(doc)))
    self.send_header('Last-Modified',
        self.date_time_string(os.stat(realpath).st_mtime))
    self.end_headers()
    if request_method == 'GET':
        self.wfile.write(doc)
    return None

def HTML_server_info(self, request_method):
    '''Generate some informations about server.'''
    m = []
    r = lambda d, i: ('<tr>'
            f'<td>{html.escape(str(d).strip())}</td>'
            f'<td>{html.escape(str(i).strip())}</td>'
            '</tr>')
    for k, v in _info.items():
        if k == 'server_start_uptime':
            m.append(
                r('server_start', self.date_time_string(v)) +
                r('server_uptime', server_uptime(v)))
        elif k == 'server_address':
            ap = self.headers['host'] + ('' if v[1]==80 else f':{v[1]}')
            m.append('<tr>'
                f'<td>{k}</td>'
                f'<td><a href="//{ap}/">{ap}</a></td>'
                '</tr>')
        else:
            m.append(r(k, v))
    n = [r(k, v) for k, v in self.headers.items()]
    self.send_response(HTTPStatus.OK)
    self.send_header('Content-type', 'text/html; charset=utf-8')
    o = [r(*v.decode().strip().split(':',1)) for v in self._headers_buffer[1:]]
    o.insert(0, '<tr><td><i>' +
        html.escape(self._headers_buffer[0].decode().strip()) +
        '</i></td></tr>')
    head = bytes(
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<link rel="icon" type="image/png" href="data:image/png;base64,'
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAA'
            'AACklEQVQI12NgAAAAAgAB4iG8MwAAAABJRU5ErkJggg=='
        '">'
        '<style>'
        'table{'
            'width:100%;'
            'border-color:#000000;'
            'border-width:1px;'
            'border-style:solid;'
            'border-collapse:collapse;'
        '}''td{'
            'border-width:0 1px;'
            'border-style:solid;'
        '}''th{'
            'text-align:left;'
            'border-width:1px;'
            'border-style:solid;'
        '}'
        '</style>'
        '</head><body><table>' ,encoding='utf-8')
    foot = bytes('</table></body></html>', encoding='utf-8')
    srvr = bytes(f'<tr><th colspan="2">Server Info</th></tr>{"".join(m)}',
        encoding='utf-8')
    reqs = bytes(f'<tr><th colspan="2">Request Headers</th></tr>{"".join(n)}',
        encoding='utf-8')
    res1 = bytes(f'<tr><th colspan="2">Response Headers</th></tr>{"".join(o)}'
        '<tr><td>Content-Length</td><td>',
        encoding='utf-8')
    res3 = bytes('</td></tr>', encoding='utf-8')
    lna = len(head) + len(foot) + len(srvr) + len(reqs) + len(res1) + len(res3)
    lnp = lna + len(str(lna))
    if len(str(lna)) != len(str(lnp)):
        lnp += 1
    lna += len(str(lnp))
    res2 = bytes(str(lnp), encoding='utf-8')
    self.send_header('Content-Length', str(lna))
    self.end_headers()
    if request_method == 'GET':
        for v in head, srvr, res1, res2, res3, reqs, foot:
            self.wfile.write(v)
    return None

###############################################################################

class CustomHTTPRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_realpath(self, path):
        '''
        translating requested path to realpath
        '''
        # abandon query parameters
        if path.count('?'): path=path.split('?',1)[0]
        if path.count('#'): path=path.split('#',1)[0]
        try:
            path = urllib.parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        return cfg['root'] + posixpath.normpath(path)

    def guess_type(self, realpath):
        '''
        set mime, default "application/octet-stream"
        realpath must be not a directory

        TODO:
            Petimbangkan untuk menggunakan HTML_raw_file() dan
            CustomHTTPRequestHandler.path_O_rule() saja.
            Dengan konsekuensi semua permintaan klien selalu dijawab "raw file"
            (application/octet-stream), kecuali yang dari 2 metode itu.
        '''
        if realpath[realpath.rfind('/'):].count('.'):
            ext = realpath[realpath.rfind('.')+1:]
        else:
            return 'application/octet-stream'
        if ext in cfg['mime']:
            return cfg['mime'][ext]
        ext = ext.lower()
        if ext in cfg['mime']:
            return cfg['mime'][ext]
        return 'application/octet-stream'

    def redirect_permanent(self, new_url):
        self.send_response(HTTPStatus.MOVED_PERMANENTLY)
        self.send_header("Location", new_url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def path_O_rule(self, RM):
        '''
        Rules for GET and HEAD method.

        always return None
        '''
        ### URL based rules
        # /
        if self.path == '/':
            return HTML_raw_file(self, cfg['root'] + '/index.html', RM)
        # /?
        elif self.path == '/?':
            return HTML_list_directory(self, cfg['root'], RM)
        # /?info
        elif self.path == '/?info':
            return HTML_server_info(self, RM)
        # /index.html
        elif self.path == '/index.html':
            parts = urllib.parse.urlsplit(self.path)
            new_parts = (parts[0], parts[1], '/', parts[3], parts[4])
            new_url = urllib.parse.urlunsplit(new_parts)
            self.redirect_permanent(new_url)
            return None
        ### realpath based rules
        realpath = self.to_realpath(self.path)
        if os.path.isdir(realpath):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.redirect_permanent(new_url)
                return None
            return HTML_list_directory(self, realpath, RM)
        elif os.path.isfile(realpath):
            return HTML_raw_file(self, realpath, RM)
        ### 404
        # HTML_404
        self.send_error(HTTPStatus.NOT_FOUND,
            'Broken Links' if os.path.islink(realpath) else 'File not found')
        return None

    def do_GET(self):
        '''Serve a GET request.'''
        self.path_O_rule('GET')

    def do_HEAD(self):
        '''Serve a HEAD request.'''
        self.path_O_rule('HEAD')

###############################################################################

if __name__ == '__main__':
    cfg['mime'] = {ext: lst[0]
        for ent in cfg['mime']
        for lst in [ent.split()]
        for ext in lst[1:]
    }

    def servercmd(httpd):
        a, p = httpd.server_address
        print(f'Server ready at http://{a}:{p}/')
        while True:
            print('Server commands: [q]uit')
            t = input()
            if t == 'q':
                httpd.shutdown()
                break

    httpd = HTTPServer(('', cfg['port']), CustomHTTPRequestHandler)
    srvcd = Thread(target=lambda: servercmd(httpd))
    srvcd.start()
    _info = {
        'server_name': httpd.server_name,
        'server_address': httpd.server_address,
        'server_port': httpd.server_port,
        'server_start_uptime': int(time.time()),
        'server_version': httpd.RequestHandlerClass.server_version,
        'sys_version': httpd.RequestHandlerClass.sys_version,
        'address_family': httpd.address_family,
        'allow_reuse_address': httpd.allow_reuse_address,
        'request_queue_size': httpd.request_queue_size,
        'default_request_version':
            httpd.RequestHandlerClass.default_request_version,
    }
    httpd.serve_forever()
    srvcd.join()
