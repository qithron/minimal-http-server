import os
import time
import html
import urllib.parse

class listdir:
    '''generate HTML document for Directory listing

    TODO: fix listdir.html()
    '''
    htmlpath = '%(root)s/data/listdir.html'

    def __init__(self, /, *args):
        self.htmlpath = self.htmlpath % {'root': args[1]}

    def rule(self, this):
        if this.command not in ('GET', 'HEAD'):
            return False
        elif this.path == '/':
            this.path_abs = this.root + '/index.html'
            if os.path.exists(this.path_abs):
                this.send_file()
            else:
                self.html(this)
        elif this.path == '/?':
            self.html(this)
        elif os.path.isdir(this.path_abs):
            old = urllib.parse.urlsplit(this.path)
            if old.path.endswith('/'):
                self.html(this)
            else:
                # redirect browser - doing basically what apache does
                new = old[0], old[1], old[2] + '/', old[3], old[4]
                url = urllib.parse.urlunsplit(new)
                this.redirect_permanent(url)
        else:
            return False
        return True

    def html(self, this):
        path = this.path_abs
        try:
            if this.use_cache():
                return
            lst = sorted(os.listdir(path),key=lambda a: a.lower())
        except OSError:
            this.send_error(
                this.code.NOT_FOUND, 'No permission to list directory')
            return
        # top bar for navigation
        dirs = [v for v in path.removeprefix(this.root).split('/') if v]
        dirs.reverse()
        a = [f'''<a href="{('../' * (len(dirs) if dirs else 1))}?">'''
            '<span style="color:red;font-style:italic;font-weight:bold;">'
            'root</span>/</a>']
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
            fullpath = f'{path}/{fn}'
            st = os.stat(fullpath)
            sm = os.path.samefile(this.root, fullpath) \
                or fullpath == this.root + '/..'
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
            fullpath = f'{path}/{fn}'
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
            doc = f.read().split('<SPLIT>')
        head, foot = map(lambda s: bytes(s, encoding=this.enc), doc)
        doc = (head +
            bytes(navbar, encoding=this.enc) +
            bytes(info, encoding=this.enc) +
            b'<table id="lstdir">' +
            ''.join(d).encode(this.enc) +
            ''.join(e).encode(this.enc) +
            ''.join(b).encode(this.enc) +
            b'</table>' + foot)
        this.header_response(this.code.OK)
        this.header_set('Content-type', 'text/html;charset=utf-8')
        this.header_set('Content-Length', str(len(doc)))
        this.header_set('Last-Modified',
            this.date_time_string(os.stat(path).st_mtime))
        this.header_end()
        if this.command == 'GET':
            this.safe_write(doc)
        return

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
