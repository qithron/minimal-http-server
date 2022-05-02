import os
import time
from html import escape
from urllib.parse import quote

from . import ENC, HTML_DOC
from ._bar import make_html_navbar

HTML_TITLE = b'10.42.0.1:%s'
HTML_HEAD = b'<style>%s</style>'
HTML_BODY = (b'%s<p id="LS_info">'
        b'total: %d item(s), '
        b'total size: %s (%d, file only)</p>'
    b'<table id="LS">%s</table>')
PATH_CSS = '%s/data/ls.css'

CSS = (
    '#LS {'
        'border-collapse: collapse;'
        'border-color: #000000;'
        'border-style: solid;'
        'border-width: 1px 0;'
        'padding: 0 1ch;'
        'height: 1ch;'
        'width: 100%;'
    '}'
    '#LS a {'
        'text-decoration: none;'
    '}'
    '#LS a:hover {'
        'color: #ff0000 !important;'
    '}'

    '#LS tr:hover {'
        'background: #43aa64;'
    '}'
    '#LS td {'
        'border-color: #000000;'
        'border-style: solid;'
        'border-width: 1px 0;'
        'padding: 0 0.5ch;'
    '}'
    '#LS_info {'
        'margin: 1ch;'
    '}'
    '.LS_name a {'
        'color: #00007f;'
    '}'
    '.LS_date {'
        'width: 20ch;'
        'text-align: center;'
    '}'
    '.LS_size {'
        'width: 1ch;'
        'text-align: right;'
    '}'
    '.LS_icon {'
        'width: 1ch;'
        'text-align: center;'
    '}'
    '.LS_icon a {'
        'font-size: xx-small;'
        'color: #00ff00;'
    '}'
).encode(ENC)


#ICON_folder = chr(128447)
#ICON_download = chr(129035)

class ls:
    # TODO: buat anchor di setiap file, dan jangan hapus fragment url nya
    method = 'GET', 'HEAD'
    path = ''
    priority = -1

    def __init__(self, *args):
        pass

    def rule(self, this):
        if this.request.method not in self.method:
            return False
        elif this.request.path == '/?':
            self.send_html(this)
        elif this.path_abs == this.root:
            if this.redirect_path_equal('/'):
                for fn in this.index_file:
                    rp = os.path.join(this.path_abs, fn)
                    if os.path.exists(rp):
                        this.path_abs = rp
                        this.send_file()
                        break
                else:
                    self.send_html(this)
        elif os.path.isdir(this.path_abs):
            if this.redirect_path_equal(os.path.normpath(this.url.path) + '/'):
                self.send_html(this)
        else:
            return False
        return True

    def send_html(self, this):
        path = this.path_abs
        if this.send_304():
            return
        try:
            lst = sorted(os.listdir(path), key=lambda a: a.lower())
        except OSError:
            this.send_error(this.code.NOT_FOUND, 'Unable to list directory')
            return

        def items():
            for name in lst:
                fullpath = os.path.join(path, name)
                exists = os.path.exists(fullpath)
                st = os.stat(fullpath, follow_symlinks=exists)
                date = st.st_mtime
                if not exists: # broken links
                    size = st.st_size
                    type = 2
                elif os.path.isdir(fullpath): # directories
                    size = '-'
                    hsze = size
                    type = 0
                else: # files
                    size = st.st_size
                    type = 1
                yield name, date, size, type

        navbar = make_html_navbar(this.url.path)
        tup = self.make_html_ls(items)

        title = HTML_TITLE % escape(this.path_rel).encode(ENC)
        head = HTML_HEAD % CSS
        body = HTML_BODY % (navbar, *tup)

        doc = HTML_DOC % (title, head, body)
        this.send_gen_html_file(doc,
            ('Last-Modified', this.date_time_string(os.stat(path).st_mtime)))

    def make_html_ls(self, items):
        a = lambda l, n, s: '<a href="%s%s"><div>%s%s</div></a>' % (l, s, n, s)
        def row():
            return ('<tr>'
                f'<td class="LS_name">{name}</td>'
                f'<td class="LS_date">{date}</td>'
                f'<td class="LS_size">{size}</td>'
                f'<td class="LS_size">{hsze}</td></tr>')
                #f'<td class="LS_icon">{icon}</td></tr>')
        d = []
        f = []
        l = []
        tsize = 0
        count = 0
        fc = 0
        for name, date, size, type in items():
            name = escape(name)
            link = quote(name)
            date = time.strftime('%Y-%b-%d %H:%M:%S', time.gmtime(date))
            match type:
                case 0: # folder
                    name = a(link, name, '/')
                    hsze = size
                    #icon = a(link, ICON_folder, '')
                    d.append(row())
                case 1: # file
                    name = a(link, name, '')
                    hsze = humanfilesize(size)
                    #icon = a(link, ICON_download, '')
                    tsize += size
                    f.append(row())
                    fc += 1
                case 2: # broken link
                    hsze = humanfilesize(size)
                    #icon = '?'
                    l.append(row())
            count += 1
        total_size = humanfilesize(tsize).encode(ENC)
        content = (''.join(d) + ''.join(f) + ''.join(l)).encode(ENC)
        return count, total_size, fc, content

def humanfilesize(size, sym=tuple('KMGTP')):
    if size < 1024:
        return str(size)
    step = -1
    while size >= 1024:
        step += 1
        size /= 1024
    s, f = str(round(size, 2)).split('.')
    return f'{s}.{f if len(f) == 2 else f"{f}0"}{sym[step]}'
