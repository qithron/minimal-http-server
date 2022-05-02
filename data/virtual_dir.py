from html import escape
from urllib.parse import quote

from . import ENC, HTML_DOC
from .ls import HTML_HEAD, CSS
from ._bar import make_html_navbar

HTML_TITLE = b'Virtual Directory'
HTML_BODY = b'%s<p id="LS_info">IMAGINATION</p><table id="LS">%s</table>'

class virtual_dir:
    method = 'GET', 'HEAD'
    path = '/;/'
    priority = 0

    def __init__(self, *args):
        self.dir = []
        for cls in args[0].addon_cls:
            if self.path is not cls.path and cls.path[:3] == self.path:
                self.dir.append(cls.path.strip('/;'))
        self.dir.sort()

    def rule(self, this):
        if this.request.method not in self.method:
            return False
        elif this.path_rel == self.path[:-1] \
        or this.request.path == self.path[:-1]:
            if this.redirect_path_equal(self.path):
                self.send_html(this)
            return True
        else:
            return False

    def send_html(self, this):
        row = lambda l, n: ('<tr><td class="LS_name">'
            '<a href="%s/"><div>%s/</div></a></td></tr>' % (l, n))
        lst = [row(quote(n), escape(n)) for n in self.dir]

        navbar = make_html_navbar(self.path)
        content = ''.join(lst).encode(ENC)

        title = HTML_TITLE
        head = HTML_HEAD % CSS
        body = HTML_BODY % (navbar, content)

        doc = HTML_DOC % (title, head, body)
        this.send_gen_html_file(doc)
