import time
from html import escape

from . import ENC, HTML_DOC
from ._bar import make_html_navbar

HTML_TITLE = b'Server Info'
HTML_HEAD = b'<style>%s</style>'
HTML_BODY = b'%s<table id=SERVER_INFO>' \
    b'<tr><th colspan="2">Server Info</th></tr>%s</table>'

CSS = (
    '#SERVER_INFO {'
        'border-color: #000000;'
        'border-width: 1;'
        'border-collapse: collapse;'
        'margin: 1ch;'
    '}'
    '#SERVER_INFO th {'
        'text-align: left;'
        'border-width: 1px;'
        'border-style: solid;'
    '}'
    '#SERVER_INFO td {'
        'border-width: 1px;'
        'border-style: solid;'
    '}'
).encode(ENC)

class server_info:
    method = 'GET', 'HEAD'
    path = '/'
    priority = 2

    def __init__(self, *args):
        self.info = (
            (args[0].server_address, 'Address'),
            (args[0].server_port, 'Port'),
            (args[0].version_string, 'Version'),
            (int(time.time()), 'START_UPTIME'))

    def rule(self, this):
        if this.request.method not in self.method:
            return False
        elif this.request.path == '/?info':
            self.send_html(this)
        else:
            return False
        return True

    def send_html(self, this):
        row = '<tr><td>%s</td><td>%s</td></tr>'
        lst = []
        for a, b in self.info:
            match b:
                case 'START_UPTIME':
                    lst.append(row % ('Started', this.date_time_string(a)))
                    lst.append(row % ('Uptime', self.server_uptime(a)))
                case 'Address':
                    a = this.request_headers['host'] \
                      + ('' if a[1] == 80 else (':' + a[1]))
                    lst.append(row % (b, '<a href="//%s/">%s</a>' % (a, a)))
                case _:
                    lst.append(row % (escape(b), escape(str(a))))

        navbar = make_html_navbar(this.url.path)
        content = ''.join(lst).encode(ENC)

        title = HTML_TITLE
        head = HTML_HEAD % CSS
        body = HTML_BODY % (navbar, content)

        doc = HTML_DOC % (title, head, body)
        this.send_gen_html_file(doc)

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
