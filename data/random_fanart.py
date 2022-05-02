import os
import time
import random
from urllib.parse import quote, unquote

if __name__ != '__main__':
    from . import ENC, HTML_DOC
    from ._bar import make_html_navbar, HTML_SEP
else:
    ENC = 'utf-8'

HTML_TITLE = b'Random Fanart: %s'
HTML_HEAD = b'<script>%s</script>'
HTML_BODY = b'%s<img style="display:block;margin:auto;" src="%s">' \
    b'<script>document.body.onload=FIRST_LOAD;</script>'

nav_HTML_next = b'<a style="color:#7f007f;" ' \
    b'href="?app=random_fanart&index=%d">next</a>'

PATH_DB = '%s/data_gen/random_fanart.db'
PATH_JS = '%s/data/random_fanart.js'

find_CMD = ('find -L %s -type f -iregex ' # TODO: use python instead?
    "'.*?\(\(\.png\)\|\(\.jpg\)\|\(\.jpeg\)\|\(\.gif\)\|\(\.bmp\)\)'")
find_PATH = '%s/main/otaku-corner/i/'
find_PATH_EXCLUDED = 'T/ichigo69.mayulive.com/', # H pics bakari :)

MAX_INDEX = 1048576 # about 1TB of 1MB images

class random_fanart:
    method = 'GET',
    path = '/'
    priority = 2

    def __init__(self, *args):
        self.path_js = PATH_JS % args[1]
        self.path_db = PATH_DB % args[1]

        self.db = random_fanart_DB(self.path_db, args[1])
        self.time = time.time()

    def rule(self, this):
        if this.request.method not in self.method:
            return False
        elif this.query.get('app') == 'random_fanart':
            if this.redirect_path_equal('/?' + this.url.query):
                self.select(this)
        else:
            return False
        return True

    def select(self, this):
        next_index = True
        if 'index' in this.query and this.query['index'].isdigit():
            redirect = False
            index = int(this.query['index'])
            next_index = index < 0 or index >= len(self.db)
        if next_index:
            redirect = True
            index = random.randint(1, len(self.db)-1)

        s = self.db[index]
        while not s:
            next_index = random.randint(1, len(self.db)-1)
            s = self.db[next_index]
            if s:
                redirect = index != next_index
                index = next_index

        while True:
            next_index = random.randint(1, len(self.db)-1)
            if self.db[next_index] and next_index != index:
                break

        nav_next = nav_HTML_next % next_index
        path = self.db.prefix + s
        patdd = unquote(path)
        js = open(self.path_js, 'rb').read()
        navbar = make_html_navbar(patdd, '/', _1=(HTML_SEP, nav_next))

        title = HTML_TITLE % os.path.basename(patdd).encode(ENC)
        head = HTML_HEAD % js
        body = HTML_BODY % (navbar, path)

        doc = HTML_DOC % (title, head, body)
        if redirect:
            this.send_307(this.url.path + '?app=random_fanart&index=%d'%index)
        else:
            this.send_gen_html_file(doc)

    @staticmethod
    def gen_data(root):
        path = find_PATH % root
        i = len(path)
        lsdir = os.popen(find_CMD % path).read().split('\n')
        lst = []
        for p in lsdir:
            for s in find_PATH_EXCLUDED:
                if s in p:
                    break
            else:
                lst.append(p[i:])
        return lst

class random_fanart_DB:
    '''simple database to keep random seed consistency'''

    @staticmethod
    def gen(root, find_path, db_save_path, max_index=MAX_INDEX):
        find_path = find_path.lstrip('/')
        path = os.path.join(root, find_path)
        i = len(path)
        lst = set(os.popen(find_CMD % path).read().strip().split('\n'))
        with open(db_save_path, 'wb') as f:
            f.write(quote(find_path).encode(ENC))
            for p in lst:
                f.write(b'\n')
                f.write(quote(p[i:]).encode(ENC))
            for _ in range(MAX_INDEX - len(lst)):
                f.write(b'\n')
            f.write(b'\n')

    def __init__(self, path, root):
        self.root = root
        self.path = path
        self.list = []
        with open(self.path, 'rb') as f:
            head = f.readline().strip()
            f.seek(0)
            while f.readline():
                self.list.append(f.tell())
        self.prefix, self.enc, last_idx = head.split(b';')
        last_idx = last_idx.lstrip(b'0')
        self.last_idx = int(last_idx) if last_idx else 0
        self.len = len(self.list)-1

    def __len__(self):
        return self.len

    def __getitem__(self, i):
        i = i + (len(self.list)*(i<0)) + (1*(i>=0))
        s = self.list[i-1]
        l = self.list[i] - s - 1
        with open(self.path, 'rb') as f:
            f.seek(s)
            r = f.read(l)
        return r

    def optimize(self):
        pass

    def update(self):
        pass

    def new_root(self, root):
        pass

if __name__ == '__main__':
    root = '/mnt/asd/.qtr/pub/www'
    path_db = '%s/data_gen/random_fanart.db' % root
    find_path = find_PATH % root
    a = lambda: random_fanart_DB(path_db)
