import os
from html import escape
from urllib.parse import quote

from . import ENC

HTML_BODY = b'<style>%s</style><div id="NAVBAR"><table>%s</table></div>'

HTML_ICON = b'<a class="NAVBAR_icon" href="%s/">:::</a>'
HTML_ROOT = b'<a class="NAVBAR_root" href="%s/?">/</a>'
HTML_PATH = b'<a class="NAVBAR_path" href="%s">%s</a>'
HTML_SEP = b'<span class="NAVBAR_sep"></span>'

CSS = (
    '#NAVBAR {'
        'background: #43aa64;'
        'border-color: #000000;'
        'border-style: solid;'
        'border-width: 1px 0;'
    '}'
    '#NAVBAR table {'
        'border-width: 0;'
        'border-collapse: collapse;'
    '}'
    '#NAVBAR a {'
        'color: #000000;'
        'text-decoration: none;'
    '}'
    '#NAVBAR a:hover {'
        'color: #ff0000 !important;'
    '}'
    '.NAVBAR_icon {'
    '}'
    '.NAVBAR_root {'
        'font-weight: bold;'
    '}'
    '.NAVBAR_path {'
    '}'
    '.NAVBAR_sep {'
        'padding: 0.5ch;'
        'margin: 0;'
    '}'
).encode(ENC)

def make_path_link(path, rel_path=None):
    '''
    path:
        path like object, make sure path to directory end with slash
            "/main/directory/file.ext"   # file
            "/main/directory"            # file
            "/"                          # directory
            "/main/directory/"           # directory
    rel_path:
        relative path, default: current directory (path)
    '''
    if rel_path is None:
        rel_path = os.path.dirname(path)
    p = '/'
    r = quote(os.path.relpath(p, rel_path)).encode(ENC)
    lst = [HTML_ROOT % r]
    paths = [s for s in path.split('/') if s]
    for v in paths[:-1]:
        p += v + '/'
        s = quote(os.path.relpath(p, rel_path)).encode(ENC) + b'/'
        v = escape(v + '/').encode(ENC)
        lst.append(HTML_PATH % (s, v))
    if paths:
        p = '' if path.startswith('/') else '/'
        d = '/' if path.endswith('/') else ''
        s = quote(os.path.relpath(p + path, rel_path) + d).encode(ENC)
        v = escape(paths[-1] + d).encode(ENC)
        lst.append(HTML_PATH % (s, v))
    return b''.join(lst), r

def make_bar(*rows):
    gen = (b'<tr><td>' + b''.join(row) + b'</td></tr>' for row in rows)
    return b''.join(gen)

def make_html_navbar(path, rel_path=None, /, *rows, **kwargs):
    path_link, r = make_path_link(path, rel_path)
    icon = HTML_ICON % r
    row = []
    if '_0' in kwargs:
        row.extend(kwargs['_0'])
    row.append(icon)
    if '_1' in kwargs:
        row.extend(kwargs['_1'])
    row.append(HTML_SEP)
    if '_2' in kwargs:
        row.extend(kwargs['_2'])
    row.append(path_link)
    if '_3' in kwargs:
        row.extend(kwargs['_3'])
    table = make_bar(row, *rows)
    return HTML_BODY % (CSS, table)
