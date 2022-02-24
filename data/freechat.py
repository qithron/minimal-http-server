import random
import time
import threading
import queue
import sqlite3
import html
import email
import json

class freechat:
    '''
    TODO: fix JS, freechat.request_update() not working jika database kosong
    TODO: add "current offline", but it's spooky-spooky :)
    TODO: add zoneinfo, query &zoneinfo=Asia/Jakarta
    '''

    dbpath = '%(root)s/data/freechat.db'
    htmlpath = '%(root)s/data/freechat.html'
    queue = None
    thread = None
    lastitem = None

    def __init__(self, /, *args):
        self.dbpath = self.dbpath % {'root': args[1]}
        self.htmlpath = self.htmlpath % {'root': args[1]}
        sql = sqlite3.connect(self.dbpath)
        cur = sql.cursor()
        cur.execute(
            'CREATE TABLE IF NOT EXISTS log ('
            'idx CHAR(17) NOT NULL, '
            'name CHAR(32) NOT NULL, '
            'text BLOB NOT NULL, '
            'PRIMARY KEY (idx))')
        sql.commit()
        i = list(cur.execute('SELECT idx FROM log ORDER BY idx DESC LIMIT 1'))
        if i and i[0]:
            self.lastitem = i[0][0]
        else:
            self.lastitem = ''
        sql.close()
        self.queue = queue.SimpleQueue()
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()

    def rule(self, this):
        if this.command not in ('GET', 'HEAD', 'POST'):
            return False
        elif not this.query or this.query['app'] != 'freechat':
            return False
        elif this.command == 'POST':
            if 'username' in this.query:
                self.request_post(this)
            else:
                return False
        elif 'mode' in this.query and this.query['mode'] == 'retrieve':
            self.request_retrieve(this)
        elif 'mode' in this.query and this.query['mode'] == 'update':
            self.request_update(this)
        elif this.path == '/?app=freechat':
            self.html(this)
        else:
            return False
        return True

    def worker(self):
        sql = sqlite3.connect(self.dbpath)
        cur = sql.cursor()
        while True:
            try:
                name, text = self.queue.get(True, 10)
            except queue.Empty:
                sql.close()
                name, text = self.queue.get()
                sql = sqlite3.connect(self.dbpath)
                cur = sql.cursor()
            idx = str(time.time()).replace('.','')
            if len(idx) != 17:
                idx += '0'*(17-len(idx))
            try:
                cur.execute(
                    'INSERT INTO log VALUES (?, ?, ?)', (idx, name, text))
            except sqlite3.IntegrityError as e:
                print(e)
            sql.commit()
            self.lastitem = idx

    def html(self, this):
        sql = sqlite3.connect(self.dbpath)
        lst = list(sql.cursor().execute(
            'SELECT * FROM log ORDER BY idx DESC LIMIT 20'))
        sql.close()
        lst = self.mk_chatbox(lst, this.enc)
        lst.insert(0,
            '<div class="chatbox" style="background-color:#00ff00;">'
                '<div class="chathead">'
                '<span class="chatname" style="color:#ff0000;">Admin</span>'
            '</div>'
            '<span class="chattext" style="white-space:normal;">'
                'Youkoso<br>'
                '<br>'
                'yang penting jangan spam, atau ... spam ajalah kalo bisa :)'
            '</span>'
            '</div>')
        with open(self.htmlpath) as f:
            doc = f.read().replace('sudo rm -rf --no-preserve-root /',
                'guest-'+random.randbytes(13).hex()).split('<SPLIT>')
        head, foot = map(lambda s: bytes(s, encoding=this.enc), doc)
        doc = head + bytes(''.join(reversed(lst)), encoding=this.enc) + foot
        this.header_response(this.code.OK)
        this.header_set('Content-type', 'text/html;charset=utf-8')
        this.header_set('Content-Length', str(len(doc)))
        this.header_end()
        if this.command == 'GET':
            this.safe_write(doc)

    def request_post(self, this):
        name = this.query['username']
        if 2 > len(name) or len(name) > 32:
            this.send_error(this.code.BAD_REQUEST, 'You NaughtyNaughty :)')
            return None
        length = int(this.headers.get('content-length'))
        if not length or length > 65535:
            this.send_error(this.code.BAD_REQUEST, 'You NaughtyNaughty :)')
            return None
        this.header_response(this.code.OK)
        this.header_end()
        text = this.safe_read(length).strip()
        if not text or len(text) > 65535:
            return None
        self.queue.put((name, text))
        return None

    def request_retrieve(self, this):
        idx = this.query['idx']
        sql = sqlite3.connect(self.dbpath)
        lst = list(sql.cursor().execute(
            'SELECT * FROM log WHERE idx < ? ORDER BY idx DESC LIMIT ?',
            (idx, 20)))
        sql.close()
        if not lst:
            this.header_response(this.code.OK)
            this.header_set('Content-Length', '0')
            this.header_end()
        else:
            lst = self.mk_chatbox(lst, this.enc)
            doc = bytes(json.dumps(lst), encoding=this.enc)
            this.header_response(this.code.OK)
            this.header_set('Content-type', 'application/json')
            this.header_set('Content-Length', str(len(doc)))
            this.header_end()
            if this.command == 'GET':
                this.safe_write(doc)

    def request_update(self, this):
        idx = this.query['idx']
        if len(idx) != 17:
            this.header_response(this.code.NOT_FOUND)
            return None
        if idx == self.lastitem:
            n = 0
            while idx == self.lastitem and n < 40:
                time.sleep(1.5)
                n += 1
        if idx == self.lastitem:
            this.header_response(this.code.OK)
            this.header_end()
        else:
            sql = sqlite3.connect(self.dbpath)
            lst = list(sql.cursor().execute(
                'SELECT * FROM log WHERE idx > ? ORDER BY idx LIMIT ?',
                (idx, 50)))
            sql.close()
            if not lst:
                print(idx, self.lastitem)
                this.header_response(this.code.INTERNAL_SERVER_ERROR)
                return None
            lst = self.mk_chatbox(lst, this.enc)
            doc = bytes(json.dumps(lst), encoding=this.enc)
            this.header_response(this.code.OK)
            this.header_set('Content-type', 'application/json')
            this.header_set('Content-Length', str(len(doc)))
            this.header_end()
            if this.command == 'GET':
                this.safe_write(doc)
            return None

    @staticmethod
    def mk_chatbox(iterable, enc):
        return [
            '<div class="chatbox" id="'
                + idx +
            '"><div class="chathead">'
            '<span class="chatdate">'
                + email.utils.formatdate(int(idx[:-7]), usegmt=True) +
            '</span>'
            '<span class="chatname">'
                + html.escape(name) +
            '</span>'
            #'<button>reply</button>'
            '</div><span class="chattext">'
                + html.escape(text.decode(encoding=enc)) +
            '</span></div>'
            for idx, name, text in iterable]
