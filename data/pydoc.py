import os
import sys
import pkgutil
import platform
import pydoc as real_pydoc
from html import escape

from . import ENC, HTML_DOC
from ._bar import make_html_navbar

HTML_TITLE = b'Pydoc: Index of Modules'
HTML_HEAD = b'<style>%s</style><script>%s</script>'
HTML_BODY = b'%s<script>document.body.onload=FIRST_LOAD;</script>'

PATH_JS = '%s/data/pydoc.js'

CSS = (
    'body {'
        'background-color:#cfff7f;'
    '}'
    'a {'
        'text-decoration:none;'
    '}'
    'a:hover {'
        'color:#ff0000 !important;'
        'text-decoration:none;'
    '}'
    '.ot {'
        'background-color:#79b94e;'
        'border-color:#2e3a2e;'
        'border-width:2px;'
        'border-style:solid;'
        'margin:0.5rem;'
    '}'
    '.ot p {'
        'background-color:#00ff00;'
        'border-width:0;'
        'padding:0.5ch;'
        'margin:0;'
    '}'
    '.in {'
        'padding:0.5rem;'
        'display:flex;'
        'flex-wrap:wrap;'
        'flex-direction:column;'
        'align-content:flex-start;'
        'align-items:flex-start;'
        'justify-content:flex-start;'
    '}'
    '.in a {'
        'margin:0;'
    '}'
    '.in .pkg {'
        'font-weight:bold;'
    '}'
).encode(ENC)

page_HTML_HEAD = b'<style>body{background-color:#f0f0f8;}</style>'
page_HTML_BODY = b'%s<div>%s</div>'

class pydoc:
    '''hackable pydoc :) rewrite of pydoc (not yet, currently, just work)

    TODO: override error page in pydoc.page()
    TODO:     tetap 200 jika ada masalah import
    '''

    method = 'GET', 'HEAD'
    path = '/;/pydoc/'
    priority = 1

    def __init__(self, *args):
        self.path_js = PATH_JS % args[1]

    def rule(self, this):
        if this.request.method not in self.method:
            return False
        elif not this.path_rel.startswith(self.path[:-1]):
            return False
        if this.path_rel == self.path[:-1]:
            if this.redirect_path_equal(self.path):
                self.send_html_index(this)
        else:
            self.send_html_page(this)
        return True

    def send_html_index(self, this):
        he = lambda a: escape(a)
        width = 0
        names = [n for n in sorted(sys.builtin_module_names)]
        # builtin
        builtin = ['<div class="ot"><p>Built-in Modules</p><div class="in">']
        for name in names:
            text = he(name)
            link = he(name)
            builtin.append(f'<a href="{link}">{text}</a>')
            if len(name)+1 > width:
                width = len(name)+1
        builtin.append('</div></div>')
        # modules
        modules = []
        for i, dn in enumerate(sorted(sys.path), start=1):
            modules.append(f'<div class="ot"><p>{he(dn)}</p><div class="in">')
            lst = []
            for imp, name, ispkg in sorted(
            list(pkgutil.iter_modules([dn])), key=lambda i: i.name.lower()):
                text = he(name)
                link = he(name)
                if ispkg:
                    lst.append(f'<a href="{link}" class="pkg">{text}</a>')
                else:
                    lst.append(f'<a href="{link}">{text}</a>')
                if len(name)+1 > width:
                    width = len(name)+1
            modules.extend(lst)
            modules.append('</div></div>')
        builtin.insert(0, '<style>.in a{width:%dch;}</style>' % width)

        js = open(self.path_js, 'rb').read()
        navbar = make_html_navbar(this.url.path)
        content = bytes(''.join(builtin) + ''.join(modules), encoding=ENC)

        title = HTML_TITLE
        head = HTML_HEAD % (CSS, js)
        body = HTML_BODY % (navbar + content)

        doc = HTML_DOC % (title, head, body)

        this.header_response(this.code.OK)
        this.header_set('Content-type', this.html_content_type)
        this.header_set('Content-Length', str(len(doc)))
        this.header_end()
        if this.request.method == 'GET':
            this.safe_write(doc)

    def send_html_page(self, this):
        name = os.path.basename(this.path_abs).removesuffix('.html')
        try:
            obj = real_pydoc.locate(name, forceload=1)
        except real_pydoc.ErrorDuringImport as e:
            this.send_error(this.code.NOT_FOUND, str(e))
            return
        if obj is None:
            this.send_error(this.code.NOT_FOUND)
            return

        navbar = make_html_navbar(this.url.path)
        ver = ("<div>Python %s [%s, %s]<br>%s</div>" % (
            escape(platform.python_version()),
            escape(platform.python_build()[0]),
            escape(platform.python_compiler()),
            escape(platform.platform(terse=True)))).encode(ENC)
        ctn = real_pydoc.HTMLDoc().document(obj, name).encode(ENC)

        title = real_pydoc.describe(obj).encode(ENC)
        head = page_HTML_HEAD
        body = page_HTML_BODY % (navbar + ver, ctn)

        doc = HTML_DOC % (title, head, body)
        this.send_gen_html_file(doc)
