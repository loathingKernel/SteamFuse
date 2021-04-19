'''
Documentation, License etc.

@package steamfuse
'''

import os
import sys
import re

import vdf
import orjson
from pathlib import Path
from fusepy.fuse import FUSE
#from fuse import FUSE
from passthrough import Passthrough
from xdg import BaseDirectory


class SteamPath(object):
    def __init__(self):
      return

class SteamFuse(Passthrough):
    def __init__(self, root):
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
        for app in orjson.loads(open('applist.json', 'r').read())['applist']['apps']:
            self.remote_appids.update({str(app['appid']): app['name']})

        chars = list()
        for i in self.local_appids.values():
            for c in i:
                if c not in chars:
                    chars.append(c)
        chars.sort()
        print(chars)
        self.re_path = re.compile(r'(\d\d\d+)\ \(([\s\w\.:\-\!]+)\)[\ \(r\)]*')
        self.re_acf = re.compile(r'(app(?:manifest|workshop)_)(\d\d\d+).acf')
    
    # Helpers
    # =======
    def _full_path(self, partial):
        print("partial before: " + partial)
        result = self.re_path.search(partial)
        if result:
            id, name = result.group(1), result.group(2)
            if id in self.local_appids:
                if self.local_appids[id] == name:
                    partial = re.sub(self.re_path, id, partial)
            if id in self.remote_appids:
                if self.remote_appids[id] == name:
                    partial = re.sub(self.re_path, id, partial)
        print("partial after: " + partial)
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
            'st_atime', 'st_ctime','st_gid', 'st_mode', 'st_mtime',
            'st_nlink', 'st_size', 'st_uid', 'st_blocks'))

    def readdir(self, path, fh):
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dir_list = os.listdir(full_path)
            for idx, appid in enumerate(dir_list):
                result = self.re_acf.search(appid)
                if result:
                    appid = result.group(2)
                    dir_list[idx] = re.sub(self.re_acf, "{0}{1} ({2}).acf".format(result.group(1), appid, self.local_appids[appid]), dir_list[idx])
                elif appid in self.local_appids.keys():
                    appname = self.local_appids[appid]
                    dir_name = "{0} ({1})".format(appid, appname)
                    dir_list[idx] = dir_name
                elif appid in self.remote_appids.keys():
                    appname = self.remote_appids[appid]
                    dir_name = "{0} ({1}) (r)".format(appid, appname)
                    dir_list[idx] = dir_name
            dirents.extend(dir_list)
        for r in dirents:
            yield r

    # File methods
    # ============


def main(root, mountpoint=None):
    if mountpoint is None:
        mountpoint = BaseDirectory.save_data_path("SteamFuse")
    try:
        FUSE(SteamFuse(root), mountpoint, nothreads=True, foreground=True)
    except RuntimeError:
        pass


if __name__ == '__main__':
    if len(sys.argv) > 2:
        main(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1])
