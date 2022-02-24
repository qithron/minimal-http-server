import os
import sys
import pkgutil
import platform
import pydoc as real_pydoc
import html
import urllib.parse

class pydoc:
    '''hackable pydoc :) rewrite of pydoc (not yet, currently, just work)

    TODO: override error page in pydoc_html.page()
    TODO:     tetap 200 jika ada masalah import
    '''

    csspath = '%(root)s/data/pydoc.css'
    htmlpath = '%(root)s/data/pydoc.html'

    def __init__(self, /, *args):
        self.csspath = self.csspath % {'root': args[1]}
        self.htmlpath = self.htmlpath % {'root': args[1]}

    def rule(self, this):
        if this.command not in ('GET', 'HEAD'):
            return False
        elif this.path == '/pydoc/':
            self.html_index(this)
        elif this.path == '/pydoc':
            old = urllib.parse.urlsplit(this.path)
            new = old[0], old[1], old[2] + '/', old[3], old[4]
            url = urllib.parse.urlunsplit(new)
            this.redirect_permanent(url)
        elif this.path == '/pydoc/pydoc.css':
            this.path_abs = self.csspath
            this.send_file()
        elif this.path.startswith('/pydoc/') and this.path.endswith('.html'):
            self.html_page(this)
        else:
            return False
        return True

    def html_index(self, this):
        he = lambda a: html.escape(a)
        width = 0
        names = [n for n in sorted(sys.builtin_module_names)]
        # builtin
        builtin = ['<div class="ot"><p>Built-in Modules</p><div class="in">']
        for name in names:
            text = he(name)
            link = he(name) + '.html'
            builtin.append(f'<a href="{link}">{text}</a>')
            if len(name)+1 > width:
                width = len(name)+1
        builtin.append('</div></div>')
        modules = []
        for i, dn in enumerate(sorted(sys.path), start=1):
            modules.append(f'<div class="ot"><p>{he(dn)}</p><div class="in">')
            lst = []
            for imp, name, ispkg in sorted(
            list(pkgutil.iter_modules([dn])), key=lambda i: i.name.lower()):
                text = he(name)
                link = he(name) + '.html'
                if ispkg:
                    lst.append(f'<a href="{link}" class="pkg">{text}</a>')
                else:
                    lst.append(f'<a href="{link}">{text}</a>')
                if len(name)+1 > width:
                    width = len(name)+1
            modules.extend(lst)
            modules.append('</div></div>')
        builtin.insert(0, '<style>.in a{width:%dch;}</style>' % width)
        with open(self.htmlpath) as f:
            doc = f.read().split('<SPLIT>')
        head, foot = map(lambda s: bytes(s, encoding=this.enc), doc)
        doc = (head
            + bytes(''.join(builtin), encoding=this.enc)
            + bytes(''.join(modules), encoding=this.enc)
            + foot)
        this.header_response(this.code.OK)
        this.header_set('Content-type', 'text/html;charset=utf-8')
        this.header_set('Content-Length', str(len(doc)))
        this.header_end()
        if this.command == 'GET':
            this.safe_write(doc)
        return

    def html_page(self, this):
        class _HTMLDoc(real_pydoc.HTMLDoc):
            def page(self, title, pyver, contents):
                """Format an HTML page."""
                css_path = '/data/pydoc-page.css'
                css_link = (
                    '<link rel="stylesheet" type="text/css" href="%s">' %
                    css_path)
                return ('<!doctype html>'
                    '<html><head><title>Pydoc: %s</title>'
                    '<meta http-equiv="Content-Type" '
                        'content="text/html; charset=utf-8">%s</head>'
                    '<body>%s<div>%s</div></body></html>' %
                    (title, css_link, pyver, contents))
        html = _HTMLDoc()

        url = os.path.basename(this.path_abs).removesuffix('.html')
        try:
            obj = real_pydoc.locate(url, forceload=1)
        except real_pydoc.ErrorDuringImport as e:
            this.send_error(this.code('NOT_FOUND'), str(e))
            return
        if obj is None:
            this.send_error(this.code('NOT_FOUND'))
            return
        title = real_pydoc.describe(obj)
        pyver = ("<div>Python %s [%s, %s]<br>%s</div>" % (
            html.escape(platform.python_version()),
            html.escape(platform.python_build()[0]),
            html.escape(platform.python_compiler()),
            html.escape(platform.platform(terse=True))))
        content = html.document(obj, url)

        doc = bytes(html.page(title, pyver, content), encoding=this.enc)
        this.header_response(this.code.OK)
        this.header_set('Content-type', 'text/html;charset=utf-8')
        this.header_set('Content-Length', str(len(doc)))
        this.header_end()
        if this.command == 'GET':
            this.safe_write(doc)
        return
