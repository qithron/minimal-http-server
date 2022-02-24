import time
import html

class serverinfo:
    htmlpath = '%(root)s/data/serverinfo.html'
    info = None

    def __init__(self, /, *args):
        self.ServerClass = args[0]
        self.htmlpath = self.htmlpath % {'root': args[1]}
        self.info = {
            'server_name': self.ServerClass.server_name,
            'server_address': self.ServerClass.server_address,
            'server_port': self.ServerClass.server_port,
            'server_start_uptime': int(time.time()),
            'server_version':
                self.ServerClass.RequestHandlerClass.server_version,
            'sys_version': self.ServerClass.RequestHandlerClass.sys_version,
            'address_family': self.ServerClass.address_family,
            'allow_reuse_address': self.ServerClass.allow_reuse_address,
            'request_queue_size': self.ServerClass.request_queue_size,
        }

    def rule(self, this):
        if this.command not in ('GET', 'HEAD'):
            return False
        elif this.path == '/?info':
            self.html(this)
        else:
            return False
        return True

    def html(self, this):
        row = lambda d, i: ('<tr>'
                f'<td>{html.escape(str(d).strip())}</td>'
                f'<td>{html.escape(str(i).strip())}</td>'
                '</tr>')
        info = []
        for k, v in self.info.items():
            if k == 'server_start_uptime':
                info.append(
                    row('server_start', this.date_time_string(v)) +
                    row('server_uptime', self.server_uptime(v)))
            elif k == 'server_address':
                ap = this.headers['host'] + ('' if v[1]==80 else f':{v[1]}')
                info.append('<tr>'
                    f'<td>{k}</td>'
                    f'<td><a href="//{ap}/">{ap}</a></td>'
                    '</tr>')
            else:
                info.append(row(k, v))
        reqhead = [row(k, v) for k, v in this.headers.items()]
        this.header_response(this.code.OK)
        this.header_set('Content-type', 'text/html;charset=utf-8')
        reshead = [row(*v.split(':',1)) for v in this.headerr[1:]]
        reshead.insert(0, '<tr><td><i>' +
            html.escape(this.headerr[0]) +
            '</i></td></tr>')
        with open(self.htmlpath) as f:
            doc = f.read().replace('\reqhead','').split('<SPLIT>')
        head, foot = map(lambda s: bytes(s, encoding=this.enc), doc)
        exth = bytes('<table>', encoding=this.enc)
        extf = bytes('</table>', encoding=this.enc)
        srvr = bytes(
            f'<tr><th colspan="2">Server Info</th></tr>{"".join(info)}',
            encoding=this.enc)
        reqs = bytes(
            f'<tr><th colspan="2">Request Headers</th></tr>{"".join(reqhead)}',
            encoding=this.enc)
        res1 = bytes(
            f'<tr><th colspan="2">Response Headers</th></tr>{"".join(reshead)}'
            '<tr><td>Content-Length</td><td>',
            encoding=this.enc)
        res3 = bytes('</td></tr>', encoding=this.enc)
        lna = len(head) + len(foot) + len(exth) + len(extf) \
            + len(srvr) + len(reqs) + len(res1) + len(res3)
        lnp = lna + len(str(lna))
        if len(str(lna)) != len(str(lnp)):
            lnp += 1
        lna += len(str(lnp))
        res2 = bytes(str(lnp), encoding=this.enc)
        this.header_set('Content-Length', str(lnp))
        this.header_end()
        if this.command == 'GET':
            for v in head, exth, srvr, res1, res2, res3, reqs, extf, foot:
                this.safe_write(v)

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
