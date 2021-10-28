'''
Documentation, License etc.

@package steamfuse
'''

import os
import re
import subprocess

import orjson
import vdf
from passthrough.passthrough import Passthrough


class SteamPath(object):
    def __init__(self):
        return


class SteamFuse(Passthrough):
    def __init__(self, root, applist, mountpoint):
        super(SteamFuse, self).__init__(root)
        self.root = os.path.join(root, 'steamapps')
        vdf_data = vdf.load(open(os.path.join(self.root, "libraryfolders.vdf"), 'r'))
        self.other_roots = [
            os.path.join(folder['path'], 'steamapps') for key, folder in vdf_data["libraryfolders"].items()
            if key.isdigit() and int(key) > 0
        ]

        self.mountpoint = mountpoint
        self.mergerfs_mount = os.path.join(mountpoint, 'mergerfs')
        self.steamfuse_mount = os.path.join(mountpoint, 'steamfuse')

        proc = subprocess.Popen(
            ['mergerfs', f'{self.root}:{":".join(self.other_roots)}', f'{self.mergerfs_mount}'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, text=True)
        out, err = proc.communicate()
        if err:
            exit(-1)

        self.local_appids = dict()
        for file in os.listdir(self.mergerfs_mount):
            if file.endswith('.acf'):
                vdf_data = vdf.load(open(os.path.join(self.mergerfs_mount, file), 'r'))
                self.local_appids.update({vdf_data["AppState"]["appid"]: vdf_data["AppState"]["installdir"]})

        self.remote_appids = dict()
        for app in orjson.loads(open(applist, 'r').read())['applist']['apps']:
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

    def __del__(self):
        proc = subprocess.Popen(
            ['fusermount', '-u', f'{self.mergerfs_mount}'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, text=True)
        out, err = proc.communicate()
        if err:
            exit(-1)

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
        path = os.path.join(self.mergerfs_mount, partial)
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
