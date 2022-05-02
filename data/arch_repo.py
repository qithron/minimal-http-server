import os

PATH_CACHE = '/mnt/asd/pkg/'
PATH_DB = '/var/lib/pacman/sync/'
DB = 'core.db', 'extra.db', 'community.db'

class arch_repo:
    method = 'GET', 'HEAD'
    path = '/arch_repo/'
    priority = 0

    def __init__(self, *args):
        pass

    def rule(self, this):
        if this.request.method not in self.method:
            return False
        elif not this.path_rel.startswith(self.path):
            return False
        for fn in DB:
            if this.path_abs.endswith(fn):
                this.path_abs = PATH_DB + fn
                break
        else:
            this.path_abs = PATH_CACHE + os.path.basename(this.path_abs)
        if os.path.exists(this.path_abs):
            this.send_file()
        else:
            this.send_error(this.code.NOT_FOUND)
        return True
