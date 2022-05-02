import os

from . import ENC, HTML_DOC
from ._bar import make_html_navbar

HTML_TITLE = b'Test'
HTML_HEAD = b'<style>%s</style><script>%s</script>'
HTML_BODY = b'%s'

PATH_JS = '%s/data/test.js'

CSS = (
    '.TEST {'
        'background-color: #43aa64;'
        'border-color: #2e3a2e;'
        'border-width:2px;'
        'border-style:solid;'
        'margin: 1ch;'
        'padding: 0.5ch;'
    '}'
    'p {'
        'margin: 0;'
        'padding: 0;'
        'padding-left: 4ch;'
    '}'
    'span {'
        'font-weight: bold;'
    '}'
    '._1xx {color: #ffffff;}'
    '._2xx {color: #00ff00;}'
    '._3xx {color: #ffff00;}'
    '._4xx {color: #ff0000;}'
    '._5xx {color: #ff00ff;}'
).encode(ENC)


BYPASS_IP = '127.0.0.1', '10.42.0.1'

MD5_SUM = 'echo -n %s | md5sum -z -'
MD5_HDG = '6816aa26588f5eb667fce4b501dae9f6'

TEST = (
('home_page','GET','/'),
('home_page','HEAD','/'),
('home_page','POST','/'),
('serve_info','GET','/?info'),
('ls','GET','/?'),
('ls','HEAD','/?'),
('ls','GET','/main'),
('ls','GET','/main/'),
('ls','GET','/main?junk=#junk'),
('ls','GET','/main/?junk#junk'),
('ls','GET','/____'),
('random_fanart','GET','/?app=random_fanart'),
('random_fanart','HEAD','/?app=random_fanart'),
('arch_repo','HEAD','/arch_repo/core.db'),
('pydoc','GET','/;/pydoc'),
('pydoc','GET','/;/pydoc/'),
('pydoc','GET','/;/pydoc/server'),
('pydoc','GET','/;/pydoc/server.html'),
('pydoc','GET','/;/pydoc/data.ls.ls'),
('all_html_doc_index','GET','/;/all_html_doc_index'),
('all_html_doc_index','GET','/;/all_html_doc_index/'),
('all_html_doc_index','GET','/;/all_html_doc_index/python2/html/index.html'),
)

class test:
    method = 'GET',
    path = '/'
    priority = 2

    def __init__(self, /, *args):
        self.path_js = PATH_JS % args[1]

    def rule(self, this):
        if this.request.method not in self.method:
            return False
        elif this.request.path == '/?test':
            if this.address[0] in BYPASS_IP:
                self.send_html(this)
            else:
                auth = this.request_headers.get('authorization')
                if auth is not None:
                    hdg = os.popen(MD5_SUM % auth.split()[1]).read().split()[0]
                    if hdg == MD5_HDG:
                        self.send_html(this)
                    else:
                        self.send_401(this)
                else:
                    self.send_401(this)
        else:
            return False
        return True

    def send_401(self, this):
        this.header_response(this.code.UNAUTHORIZED)
        this.header_set('www-authenticate', 'Basic')
        this.header_set('Content-Type', this.html_content_type)
        this.header_set('Content-Length', '0')
        this.header_end()

    def send_html(self, this):
        lst = lambda l: ('_'.join(l), '_'.join(l), l[1], l[2])
        div = '<div class="TEST" id="%s"></div>' \
            '<script>SEND_REQ("%s","%s","%s");</script>'

        js = open(self.path_js, 'rb').read()
        navbar = make_html_navbar(this.url.path)
        content = ''.join([div % lst(v) for v in TEST]).encode(ENC)

        title = HTML_TITLE
        head = HTML_HEAD % (CSS, js)
        body = HTML_BODY % navbar + content

        doc = HTML_DOC % (title, head, body)
        this.send_gen_html_file(doc)
