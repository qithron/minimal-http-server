import os
import time
import json
from html import escape
from urllib.parse import quote

from . import ENC, HTML_DOC
from .ls import HTML_HEAD, CSS
from ._bar import make_html_navbar

HTML_TITLE = b'All Docs in /usr/share/doc/'
HTML_BODY = b'%s<p id="LS_info">/usr/share/doc/</p><table id="LS">%s</table>'

PATH_JSON = '%s/data_gen/all_html_doc_index.json'

find_CMD = ('find -L /usr/share/doc/%s -type f -iregex '
    "'.*?index\(\(\.html\)\|\(\.htm\)\)'")
find_PATH = '/usr/share/doc/'
find_PATH_EXCLUDED = {'HTML'}

class all_html_doc_index:
    method = 'GET', 'HEAD'
    path = '/;/all_html_doc_index/'
    priority = 1

    def __init__(self, *args):
        self.path_json = PATH_JSON % args[1]

        self.cache = self.gen_data(self.path_json)

    def rule(self, this):
        if this.request.method not in self.method:
            return False
        elif not this.path_rel.startswith(self.path[:-1]):
            return False
        if this.path_rel == self.path[:-1]:
            if this.redirect_path_equal(self.path):
                self.send_html(this)
        else:
            this.path_abs = os.path.join(find_PATH,
                this.url.path.removeprefix(self.path))
            if os.path.isfile(this.path_abs):
                this.send_file()
            elif os.path.isdir(this.path_abs):
                this.send_error(this.code.FORBIDDEN)
            else:
                this.send_error(this.code.NOT_FOUND)
        return True

    def send_html(self, this):
        a = lambda l, n: '<a href="%s"><div>%s/</div></a>' % (l, n)
        row = lambda *t: ('<tr><td class="LS_name">%s</td>'
            '<td class="LS_date">%s</td></tr>' % t)
        lst = []

        for name, (ipath, mt) in self.cache.items():
            path = os.path.join(find_PATH, name)
            # TODO: update using a queue
            #if not os.path.exists(path): pass
            st = os.stat(path)
            # TODO: update using a queue
            #if mt != st.st_mtime_ns: pass
            name = a(quote(ipath), escape(name))
            date = time.strftime('%Y-%b-%d %H:%M:%S', time.gmtime(st.st_mtime))
            lst.append(row(name, date))

        navbar = make_html_navbar(this.url.path)
        content = ''.join(lst).encode(ENC)

        title = HTML_TITLE
        head = HTML_HEAD % CSS
        body = HTML_BODY % (navbar, content)

        doc = HTML_DOC % (title, head, body)
        this.send_gen_html_file(doc)

    def make_html_ls(self, items):
        a = lambda l, n: '<a href="%s"><div>%s/</div></a>' % (l, n)
        def row():
            return ('<tr>'
                f'<td class="LS_name">{name}</td>'
                f'<td class="LS_date">{date}</td></tr>')
        lst = []
        for name, date, index in items():
            name = a(quote(index), escape(name))
            date = time.strftime('%Y-%b-%d %H:%M:%S', time.gmtime(date))
            lst.append(row())

    def gen_data(self, path_json):
        if os.path.exists(path_json):
            with open(path_json) as f:
                dct = json.load(f)
            rewrite = False
            for name, (ipath, mt) in dct.items():
                path = os.path.join(find_PATH, name)
                if not os.path.exists(path):
                    rewrite = True
                    del dct[name]
                elif mt != os.stat(path).st_mtime_ns:
                    rewrite = True
                    self._locate_index(dct, name)
            if rewrite:
                with open(path_json, 'w') as f:
                    json.dump(dct, f, separators=(',', ':'))
        else:
            dct = {}
            lsdir = sorted(set(os.listdir(find_PATH)) - find_PATH_EXCLUDED,
                key=lambda x: x.lower())
            for name in lsdir:
                self._locate_index(dct, name)
                if name in dct:
                    x = len(name) + 1
            with open(path_json, 'w') as f:
                json.dump(dct, f, separators=(',', ':'))
        return dct

    @staticmethod
    def _locate_index(dct, name):
        l = sorted(os.popen(find_CMD % name).read().strip().split('\n'),
            key=lambda x: len(x))
        for w in l:
            if w:
                mt = os.stat(find_PATH + name).st_mtime_ns
                dct[name] = w.removeprefix(find_PATH), mt
                break
        else:
            if name in dct:
                del dct[name]
