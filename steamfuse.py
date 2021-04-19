'''
Documentation, License etc.

@package steamfuse
'''

import os
import re
import sys

import requests
import orjson
import vdf
from xdg import BaseDirectory

from fusepy.fuse import FUSE
from passthrough import Passthrough


class SteamPath(object):
    def __init__(self):
        return


class SteamFuse(Passthrough):
    def __init__(self, root, applist):
        self.root = os.path.join(root, "steamapps")
        vdf_data = vdf.load(open(os.path.join(self.root, "libraryfolders.vdf"), 'r'))
        self.other_roots = [
            os.path.join(value, "steamapps") for key, value in vdf_data["LibraryFolders"].items() if key.isdigit()
        ]

        self.local_appids = dict()
        for library in [self.root, *self.other_roots]:
            for file in os.listdir(library):
                if file.endswith('.acf'):
                    vdf_data = vdf.load(open(os.path.join(library, file), 'r'))
                    self.local_appids.update({vdf_data["AppState"]["appid"]: vdf_data["AppState"]["installdir"]})

        self.remote_appids = dict()
        for app in orjson.loads(open(applist, 'r').read())['applist']['apps']:
            self.remote_appids.update({str(app['appid']): app['name']})

        self.re_acf = re.compile(r'(app(?:manifest|workshop)_)(\d\d\d+).acf')

        self.paths = dict()

    # Helpers
    # =======
    def _full_path(self, partial):
        try:
            partial = self.paths[partial]
        except KeyError:
            pass
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
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
                is_acf = self.re_acf.search(appid)
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
                    fuse_name = re.sub(
                        self.re_acf,
                        "{0}{1} ({2}).acf".format(
                            is_acf.group(1),
                            appid,
                            appname),
                        dir_list[idx])
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
                    fuse_path = path + "/" + fuse_name
                    if path in self.paths.keys():
                        path = self.paths[path]
                    real_path = path + "/" + real_name
                    if fuse_path not in self.paths:
                        self.paths.update({fuse_path: real_path})

                elif path in self.paths.keys():
                    fuse_path = path + "/" + real_name
                    real_path = self.paths[path] + "/" + real_name
                    if fuse_path not in self.paths:
                        self.paths.update({fuse_path: real_path})

            dirents.extend(dir_list)
        for r in dirents:
            yield r

    # File methods
    # ============


def main(root, mountpoint=None):

    applist = os.path.join(BaseDirectory.save_cache_path("SteamFuse"), "applist.json")
    if not os.path.exists(applist):
        url = 'https://api.steampowered.com/ISteamApps/GetAppList/v2/'
        res = requests.get(url, allow_redirects=True)
        open(applist, 'wb').write(res.content)

    if mountpoint is None:
        mountpoint = BaseDirectory.save_data_path("SteamFuse")
    try:
        FUSE(SteamFuse(root, applist), mountpoint, nothreads=True, foreground=True)
    except RuntimeError:
        pass


if __name__ == '__main__':
    if len(sys.argv) > 2:
        main(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1])
