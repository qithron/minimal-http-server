'''2022 https://choosealicense.com/licenses/mit/

TODO: add MIT license here, or in pj dir instead?

TODO: add cache to reduce intensive modules, ex. generated files, etc ...
TODO: remake logging
'''

import os
import threading
import shutil

import time
import datetime
import email

#import re
import urllib.parse
import html
import http.server
from http import HTTPStatus

# freechat
import sqlite3
import json
import random
import queue

# def unhumanhtml(s):
#     '''Strip HTML files to single line.'''
#     re.sub("(<!--.*?-->)", "", s, flags=re.DOTALL)

###############################################################################

class Addon:
    '''Template for addon for server class.'''

    def __init__(self, ServerClass):
        self.ServerClass = ServerClass
        #self.RequestHandlerClass = None

    def rule(self, this, realpath, query, RM):
        return False

class CustomHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    addon = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def flush_headers(self, *args, **kwargs):
        try:
            super().flush_headers(*args, **kwargs)
        except (BrokenPipeError, ConnectionResetError) as e:
            self.log_error('%s', e)

    def safeio(self, func):
        try:
            return func()
        except (BrokenPipeError, ConnectionResetError) as e:
            self.log_error('%s', e)
            return None

    def do_GET(self):
        self.rule('GET')

    def do_HEAD(self):
        self.rule('HEAD')

    def do_POST(self):
        self.rule('POST')

    @staticmethod
    def query_to_dict(path):
        query = urllib.parse.urlsplit(path).query
        if '=' not in query:
            return None
        d = {}
        for s in query.split('&'):
            l = s.split('=')
            d[l[0]] = l[1] if len(l) == 2 else ''
        return d

    @staticmethod
    def mime_types(realpath):
        basename = os.path.basename(realpath)
        if basename.count('.'):
            ext = basename.rsplit('.',1)[1]
        else:
            return 'application/octet-stream'
        if ext in conf.mime:
            return conf.mime[ext]
        ext = ext.lower()
        if ext in conf.mime:
            return conf.mime[ext]
        return 'application/octet-stream'

    def send_file(self, realpath, request_method):
        if self.use_cache(realpath):
            return None
        content_type = self.mime_types(realpath)
        stat = os.stat(realpath)
        sz = stat.st_size
        mt = stat.st_mtime
        if 'range' in self.headers:
            s, e = self.headers.get('range').split('=')[1].split('-')
            s = int(s)
            if e: e=int(e)
            else: e=sz-1
            self.send_response(HTTPStatus.PARTIAL_CONTENT)
            self.send_header('Content-type', content_type)
            self.send_header('Content-Length', str(sz))
            self.send_header('Content-Range', f'bytes {s}-{e}/{sz}')
            self.send_header('Last-Modified', self.date_time_string(mt))
            self.end_headers()
            if request_method == 'GET':
                with open(realpath, 'rb') as f:
                    f.seek(s)
                    self.safeio(lambda: shutil.copyfileobj(f, self.wfile, e))
            return None
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', content_type)
        self.send_header('Content-Length', str(sz))
        self.send_header('Last-Modified', self.date_time_string(mt))
        self.end_headers()
        if request_method == 'GET':
            with open(realpath, 'rb') as f:
                self.safeio(lambda: shutil.copyfileobj(f, self.wfile))
        return None

    def use_cache(self, realpath):
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
                        os.stat(realpath).st_mtime, datetime.timezone.utc)
                    # remove microseconds, like in If-Modified-Since
                    last_mod = last_mod.replace(microsecond=0)
                    if last_mod <= ims:
                        self.send_response(HTTPStatus.NOT_MODIFIED)
                        self.end_headers()
                        return True
        return False

    def redirect_permanent(self, new_url):
        self.send_response(HTTPStatus.MOVED_PERMANENTLY)
        self.send_header('Location', new_url)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def rule(self, RM):
        realpath = conf.root \
            + urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        query = self.query_to_dict(self.path)
        if RM == 'POST':
            if any([e.rule(self, realpath, query, RM) for e in self.addon]):
                pass
            else:
                self.send_error(HTTPStatus.NOT_IMPLEMENTED, 'Not Implemented')
            return None
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if self.path == '/?pydoc':
            self.redirect_permanent(f'http://{self.headers["Host"]}:60000/')
        elif self.path == '/favicon.ico':
            realpath = conf.root + '/main/img/one.png'
            self.send_file(realpath, RM)
        elif any([e.rule(self, realpath, query, RM) for e in self.addon]):
            pass
        # using mime types
        elif os.path.isfile(realpath):
            self.send_file(realpath, RM)
        # broken links, or not found
        else:
            self.send_error(HTTPStatus.NOT_FOUND, 'Broken Links'
                if os.path.islink(realpath) else 'File not found')
        return None

class CustomHTTPServer(http.server.ThreadingHTTPServer):
    def __init__(self, addon=None, *args, **kwargs):
        '''add "extension" to handle class'''
        super().__init__(*args, **kwargs)
        if addon:
            self.RequestHandlerClass.addon = [a(self) for a in addon]

###############################################################################

class listdir(Addon):
    '''generate HTML document for Directory listing

    TODO: fix listdir.html()
    '''
    htmlpath = '%(root)s/data/listdir.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.htmlpath = self.htmlpath % {'root': conf.root}

    def rule(self, this, realpath, query, RM):
        if RM == 'POST':
            return False
        elif this.path == '/':
            realpath = conf.root + '/index.html'
            if os.path.exists(realpath):
                this.send_file(realpath, RM)
            else:
                self.html(this, conf.root, RM)
        elif this.path == '/?':
            self.html(this, conf.root, RM)
        elif os.path.isdir(realpath):
            old = urllib.parse.urlsplit(this.path)
            if old.path.endswith('/'):
                self.html(this, realpath, RM)
            else:
                # redirect browser - doing basically what apache does
                new = old[0], old[1], old[2] + '/', old[3], old[4]
                url = urllib.parse.urlunsplit(new)
                this.redirect_permanent(url)
        else:
            return False
        return True

    def html(self, this, realpath, request_method):
        try:
            if this.use_cache(realpath):
                return None
            lst = sorted(os.listdir(realpath),key=lambda a: a.lower())
        except OSError:
            this.send_error(
                HTTPStatus.NOT_FOUND, 'No permission to list directory')
            return None
        # top bar for navigation
        dirs = [v for v in realpath.removeprefix(conf.root).split('/') if v]
        dirs.reverse()
        a = [f'''<a href="{('../' * (len(dirs) if dirs else 1))}?">'''
            '<span style="color:red;font-style:italic;font-weight:bold;">'
            'root</span>/</a>'
        ]
        for i in range(len(dirs)-1, -1, -1):
            a.append(f'''<a href="{('../'*i)}">{dirs[i]}/</a>''')
        navbar = f'<table id=navbar><tr><td>{"".join(a)}</td></tr></table>'
        # total items
        info = f'<p>total: {len(lst)} item(s)</p>'
        # entries, including . and ..
        d = [] # directories
        e = [] # files
        b = [] # broken links
        for fn in '.', '..':
            fullpath = f'{realpath}/{fn}'
            st = os.stat(fullpath)
            sm = os.path.samefile(conf.root,fullpath) \
                or fullpath == conf.root + '/..'
            name = fn
            link = fn + ('/?' if sm else '/')
            date = time.strftime('%Y-%b-%d %H:%M:%S',time.gmtime(st.st_mtime))
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
            name = html.escape(fn)
            link = urllib.parse.quote(fn)
            date = time.strftime('%Y-%b-%d %H:%M:%S',time.gmtime(st.st_mtime))
            if not exists:
                size = st.st_size
                hsze = self.humanfilesize(size)
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
                hsze = self.humanfilesize(size)
                e.append('<tr>'
                    f'<td class="name">'
                        f'<a href="{link}"><div>{name}</div></a></td>'
                    f'<td class="date">{date}</td>'
                    f'<td class="size">{size}</td>'
                    f'<td class="size">{hsze}</td>'
                    f'<td class="icon">'
                        f'<a href="{link}" download="{name}">🠋</a></td>'
                '</tr>')
        with open(self.htmlpath) as f:
            doc = f.read().replace('\n','').split('<SPLIT>')
        head, foot = map(lambda s: bytes(s, encoding='utf-8'), doc)
        doc = (head +
            bytes(navbar, encoding='utf-8') +
            bytes(info, encoding='utf-8') +
            b'<table id="lstdir">' +
            ''.join(d).encode('utf-8') +
            ''.join(e).encode('utf-8') +
            ''.join(b).encode('utf-8') +
            b'</table>' + foot
        )
        this.send_response(HTTPStatus.OK)
        this.send_header('Content-type', 'text/html; charset=utf-8')
        this.send_header('Content-Length', str(len(doc)))
        this.send_header('Last-Modified',
            this.date_time_string(os.stat(realpath).st_mtime))
        this.end_headers()
        if request_method == 'GET':
            this.safeio(lambda: this.wfile.write(doc))
        return None

    @staticmethod
    def humanfilesize(size, sym=tuple('KMGTP')):
        if size < 1024:
            return str(size)
        else:
            step = -1
            while size >= 1024:
                step += 1
                size /= 1024
            s, f = str(round(size, 2)).split('.')
            return f'{s}.{f if len(f) == 2 else f"{f}0"}{sym[step]}'

class serverinfo(Addon):
    htmlpath = '%(root)s/data/serverinfo.html'
    info = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.htmlpath = self.htmlpath % {'root': conf.root}
        self.info = {
            'server_name': self.ServerClass.server_name,
            'server_address': self.ServerClass.server_address,
            'server_port': self.ServerClass.server_port,
            'server_start_uptime': int(time.time()),
            'server_version':
                self.ServerClass.RequestHandlerClass.server_version,
            'sys_version': self.ServerClass.RequestHandlerClass.sys_version,
            'address_family': self.ServerClass.address_family,
            'allow_reuse_address': self.ServerClass.allow_reuse_address,
            'request_queue_size': self.ServerClass.request_queue_size,
            'default_request_version':
                self.ServerClass.RequestHandlerClass.default_request_version,
        }

    def rule(self, this, realpath, query, RM):
        if RM == 'POST':
            return False
        elif this.path == '/?info':
            self.html(this, RM)
        else:
            return False
        return True

    def html(self, this, request_method):
        m = []
        r = lambda d, i: ('<tr>'
                f'<td>{html.escape(str(d).strip())}</td>'
                f'<td>{html.escape(str(i).strip())}</td>'
                '</tr>')
        for k, v in self.info.items():
            if k == 'server_start_uptime':
                m.append(
                    r('server_start', this.date_time_string(v)) +
                    r('server_uptime', self.server_uptime(v)))
            elif k == 'server_address':
                ap = this.headers['host'] + ('' if v[1]==80 else f':{v[1]}')
                m.append('<tr>'
                    f'<td>{k}</td>'
                    f'<td><a href="//{ap}/">{ap}</a></td>'
                    '</tr>')
            else:
                m.append(r(k, v))
        n = [r(k, v) for k, v in this.headers.items()]
        this.send_response(HTTPStatus.OK)
        this.send_header('Content-type', 'text/html; charset=utf-8')
        o = [r(*v.decode().strip().split(':',1))
            for v in this._headers_buffer[1:]]
        o.insert(0, '<tr><td><i>' +
            html.escape(this._headers_buffer[0].decode().strip()) +
            '</i></td></tr>')
        with open(conf.root + '/data/serverinfo.html') as f:
            doc = f.read().replace('\n','').split('<SPLIT>')
        head, foot = map(lambda s: bytes(s, encoding='utf-8'), doc)
        exth = bytes('<table>', encoding='utf-8')
        extf = bytes('</table>', encoding='utf-8')
        srvr = bytes(
            f'<tr><th colspan="2">Server Info</th></tr>{"".join(m)}',
            encoding='utf-8')
        reqs = bytes(
            f'<tr><th colspan="2">Request Headers</th></tr>{"".join(n)}',
            encoding='utf-8')
        res1 = bytes(
            f'<tr><th colspan="2">Response Headers</th></tr>{"".join(o)}'
            '<tr><td>Content-Length</td><td>',
            encoding='utf-8')
        res3 = bytes('</td></tr>', encoding='utf-8')
        lna = len(head) + len(foot) + len(exth) + len(extf) \
            + len(srvr) + len(reqs) + len(res1) + len(res3)
        lnp = lna + len(str(lna))
        if len(str(lna)) != len(str(lnp)):
            lnp += 1
        lna += len(str(lnp))
        res2 = bytes(str(lnp), encoding='utf-8')
        this.send_header('Content-Length', str(lnp))
        this.end_headers()
        if request_method == 'GET':
            for v in head, exth, srvr, res1, res2, res3, reqs, extf, foot:
                this.safeio(lambda: this.wfile.write(v))

    @staticmethod
    def server_uptime(start_time):
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

class freechat(Addon):
    '''
    TODO: freechat.request_update() not working jika database kosong
    '''

    dbpath = '%(root)s/data/freechat.db'
    htmlpath = '%(root)s/data/freechat.html'
    queue = None
    thread = None
    lastitem = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dbpath = self.dbpath % {'root': conf.root}
        self.htmlpath = self.htmlpath % {'root': conf.root}
        s = sqlite3.connect(self.dbpath)
        c = s.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS log ('
                'idx CHAR(17) NOT NULL, '
                'name CHAR(32) NOT NULL, '
                'text BLOB NOT NULL, '
                'PRIMARY KEY (idx))')
        s.commit()
        r = tuple(c.execute('SELECT idx FROM log ORDER BY idx DESC LIMIT 1'))
        if r and r[0]:
            self.lastitem = r[0][0]
        else:
            self.lastitem = ''
        s.close()

        self.queue = queue.SimpleQueue()
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()

    def rule(self, this, realpath, query, RM):
        if not query or query['app'] != 'freechat':
            return False
        elif RM == 'POST':
            if 'username' in query:
                self.request_post(this, query)
            else:
                return False
        elif 'mode' in query and query['mode'] == 'retrieve':
            self.request_retrieve(this, query, RM)
        elif 'mode' in query and query['mode'] == 'update':
            self.request_update(this, query, RM)
        elif this.path == '/?app=freechat':
            self.html(this, RM)
        else:
            return False
        return True

    def worker(self):
        sql = sqlite3.connect(self.dbpath)
        cur = sql.cursor()
        while True:
            try:
                name, text = self.queue.get(True, 10)
            except queue.Empty:
                sql.close()
                name, text = self.queue.get()
                sql = sqlite3.connect(self.dbpath)
                cur = sql.cursor()
            idx = str(time.time()).replace('.','')
            if len(idx) != 17:
                idx += '0'*(17-len(idx))
            try:
                cur.execute(
                    'INSERT INTO log VALUES (?, ?, ?)', (idx, name, text))
            except sqlite3.IntegrityError as e:
                print(e)
            sql.commit()
            self.lastitem = idx

    def html(self, this, request_method):
        sql = sqlite3.connect(self.dbpath)
        lst = sql.cursor()
        lst = list(lst.execute('SELECT * FROM log ORDER BY idx DESC LIMIT 20'))
        sql.close()
        lst = self.mk_chatbox(lst)
        lst.insert(0,
            '<div class="chatbox" style="background-color:#00ff00;">'
                '<div class="chathead">'
                '<span class="chatname" style="color:#ff0000;">Admin</span>'
            '</div>'
            '<span class="chattext" style="white-space:normal;">'
                'Welcome to free chat!<br>'
                '<br>'
                'yang penting jangan spam, atau ... spam ajalah kalo bisa :)'
            '</span>'
            '</div>')
        with open(self.htmlpath) as f:
            doc = f.read().replace('sudo rm -rf --no-preserve-root /',
                'guest-'+random.randbytes(13).hex()).split('<SPLIT>')
        head, foot = map(lambda s: bytes(s, encoding='utf-8'), doc)
        doc = head + bytes(''.join(reversed(lst)), encoding='utf-8') + foot
        this.send_response(HTTPStatus.OK)
        this.send_header('Content-type', 'text/html')
        this.send_header('Content-Length', str(len(doc)))
        this.end_headers()
        if request_method == 'GET':
            this.safeio(lambda: this.wfile.write(doc))
        return None

    def request_post(self, this, query):
        name = urllib.parse.unquote(query['username'])
        if 2 > len(name) or len(name) > 32:
            this.send_error(HTTPStatus.NOT_ACCEPTABLE, 'You NaughtyNaughty :)')
            return None
        length = int(this.headers.get('content-length'))
        if not length or length > 65535:
            this.send_error(HTTPStatus.NOT_ACCEPTABLE, 'You NaughtyNaughty :)')
            return None
        this.send_response(HTTPStatus.OK)
        this.end_headers()
        text = this.safeio(lambda: this.rfile.read(length).strip())
        if not text or len(text) > 65535:
            this.send_error(HTTPStatus.NOT_ACCEPTABLE, 'You NaughtyNaughty :)')
            return None
        self.queue.put((name, text))
        return None

    def request_retrieve(self, this, query, request_method):
        idx = query['idx']
        sql = sqlite3.connect(self.dbpath)
        cur = sql.cursor()
        lst = list(cur.execute(
            'SELECT * FROM log WHERE idx < ? ORDER BY idx DESC LIMIT ?',
            (idx, 20)))
        sql.close()
        if not lst:
            this.send_response(HTTPStatus.OK)
            this.send_header('Content-Length', '0')
            this.end_headers()
        else:
            lst = self.mk_chatbox(lst)
            doc = bytes(json.dumps(lst), encoding='utf-8')
            this.send_response(HTTPStatus.OK)
            this.send_header('Content-type', 'application/json')
            this.send_header('Content-Length', str(len(doc)))
            this.end_headers()
            if request_method == 'GET':
                this.safeio(lambda: this.wfile.write(doc))

    def request_update(self, this, query, request_method):
        idx = query['idx']
        if len(idx) != 17:
            this.send_error(HTTPStatus.NOT_FOUND)
            return None
        if idx == self.lastitem:
            n = 0
            while idx == self.lastitem and n < 40:
                time.sleep(1.5)
                n += 1
        if idx == self.lastitem:
            this.send_response(HTTPStatus.OK)
            this.end_headers()
        else:
            sql = sqlite3.connect(self.dbpath)
            cur = sql.cursor()
            lst = list(cur.execute(
                'SELECT * FROM log WHERE idx > ? ORDER BY idx LIMIT ?',
                (idx, 50)))
            sql.close()
            if not lst:
                print(idx, self.lastitem)
                this.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
                return None
            lst = self.mk_chatbox(lst)
            doc = bytes(json.dumps(lst), encoding='utf-8')
            this.send_response(HTTPStatus.OK)
            this.send_header('Content-type', 'application/json')
            this.send_header('Content-Length', str(len(doc)))
            this.end_headers()
            if request_method == 'GET':
                this.safeio(lambda: this.wfile.write(doc))
            return None

    @staticmethod
    def mk_chatbox(iterable):
        return [
            '<div class="chatbox" id="'
                + idx +
            '"><div class="chathead">'
            '<span class="chatdate">'
                + email.utils.formatdate(int(idx[:-7]), usegmt=True) +
            '</span>'
            '<span class="chatname">'
                + html.escape(name) +
            '</span>'
            #'<button>reply</button>'
            '</div><span class="chattext">'
                + html.escape(text.decode(encoding='utf-8')) +
            '</span></div>'
            for idx, name, text in iterable]

conf = '%(script_path)s/data/server.conf'

if __name__ == '__main__':
    conf = conf % {'script_path': os.path.dirname(__file__)}
    with open(conf) as t:
        conf = type('conf', (), eval(t.read()))
    conf.root = os.path.normpath(conf.root)
    conf.mime = {ext: lst[0]
        for ent in conf.mime
        for lst in [ent.split()]
        for ext in lst[1:]}

    def servercmd(httpd):
        a, p = httpd.server_address
        print(f'Server ready at http://{a}:{p}/')
        while True:
            print('Server commands: [q]uit')
            t = input()
            if t == 'q':
                httpd.shutdown()
                break

    addon = (
        serverinfo,
        freechat,
        listdir, # last, because it's ignore the query
    )
    httpd = CustomHTTPServer(addon,
        (conf.addr,conf.port), CustomHTTPRequestHandler)
    srvcd = threading.Thread(target=lambda:servercmd(httpd))

    srvcd.start()
    httpd.serve_forever()
    srvcd.join()
