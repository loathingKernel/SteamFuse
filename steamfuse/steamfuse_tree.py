'''
Documentation, License etc.

@package steamfuse
'''

import os
import re

import orjson
import vdf
from .passthrough.passthrough import Passthrough


class SteamPath(object):
    def __init__(self):
        return


class SteamFuseTree(Passthrough):
    def __init__(self, root, applist):
        super(SteamFuseTree, self).__init__(root)

        self.local_appids = dict()
        for file in os.listdir(root):
            if file.endswith('.acf'):
                vdf_data = vdf.load(open(os.path.join(root, file), 'r'))
                self.local_appids.update({vdf_data["AppState"]["appid"]: vdf_data["AppState"]["installdir"]})

        self.remote_appids = dict()
        for app in orjson.loads(open(applist, 'r').read())['applist']['apps']:
            self.remote_appids.update({str(app['appid']): app['name']})

        self.re_acf = re.compile(r'(app(?:manifest|workshop)_)(\d\d\d+).acf')

        self.paths = dict()

    # Helpers
    # =======
    def _full_path(self, partial):
        partial = self._find_path(partial)
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def _find_path(self, path):
        parts = path.split('/')
        paths = [os.path.join('/', *parts[:i]) for i in range(1, len(parts)+1)]
        paths.reverse()
        for p in paths:
            try:
                path = self.paths[p]
                break
            except KeyError:
                continue
        path = os.path.join(path, *parts[len(path.split('/')):])
        return path

    # Filesystem methods
    # ==================

    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in (
            'st_atime', 'st_ctime', 'st_gid', 'st_mode', 'st_mtime',
            'st_nlink', 'st_size', 'st_uid', 'st_blocks'))

    def readdir(self, path, fh):
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dir_list = os.listdir(full_path)
            for idx, appid in enumerate(dir_list):
                is_acf = self.re_acf.search(str(appid))
                fuse_name = None
                real_name = dir_list[idx]

                if is_acf:
                    appid = is_acf.group(2)
                    if appid in self.local_appids.keys():
                        appname = self.local_appids[appid]
                    elif appid in self.remote_appids.keys():
                        appname = self.remote_appids[appid]
                    else:
                        continue
                    fuse_name = re.sub(self.re_acf,
                                       f'{is_acf.group(1)}{appid} ({appname}).acf',
                                       str(dir_list[idx]))
                    dir_list[idx] = fuse_name

                elif appid in self.local_appids.keys():
                    appname = self.local_appids[appid]
                    fuse_name = "{0} ({1})".format(appid, appname)
                    dir_list[idx] = fuse_name

                elif appid in self.remote_appids.keys():
                    appname = self.remote_appids[appid]
                    fuse_name = "{0} ({1}) (r)".format(appid, appname)
                    dir_list[idx] = fuse_name

                if fuse_name is not None:
                    fuse_path = os.path.join(path, fuse_name)
                    path = self._find_path(path)
                    real_path = os.path.join(path, real_name)
                    if fuse_path not in self.paths:
                        self.paths.update({fuse_path: real_path})

            dirents.extend(dir_list)
        for r in dirents:
            yield r

    def rename(self, old, new):
        if old in self.paths.keys():
            return None
        return os.rename(self._full_path(old), self._full_path(new))

    # File methods
    # ============
