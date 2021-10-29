import os
import subprocess
import sys

import requests
import vdf
from fuse import FUSE
from xdg import BaseDirectory

from .steamfuse_tree import SteamFuseTree
from .steamfuse_regex import SteamFuseRegex


def main(steam_path=None, mountpoint=None):

    # Setup XDG directories
    config_dir = BaseDirectory.save_config_path('steamfuse')
    data_dir = BaseDirectory.save_data_path('steamfuse')
    cache_dir = BaseDirectory.save_cache_path('steamfuse')

    # Check/Set path to steam installation
    if steam_path is None:
        steam_path = os.path.expanduser('~/.local/share/Steam')
        if not os.path.exists(steam_path):
            steam_path = os.path.expanduser('~/.var/app/com.valvesoftware.Steam/data/Steam/')
            if not os.path.exists(steam_path):
                print('Could not find Steam install dir. Specify as argument.')
                return -1

    # Find libraries and installed games
    main_library = os.path.join(steam_path, 'steamapps')
    libraryfolders_vdf = vdf.load(open(os.path.join(main_library, 'libraryfolders.vdf'), 'r'))
    more_libraries = [
        os.path.join(folder['path'], 'steamapps') for key, folder in libraryfolders_vdf['libraryfolders'].items()
        if key.isdigit() and int(key) > 0
    ]

    # Setup mergerfs mount
    mergerfs_path = os.path.join(data_dir, 'mergerfs')
    if not os.path.exists(mergerfs_path):
        os.mkdir(mergerfs_path)
    proc = subprocess.Popen(
        ['mergerfs', f'{main_library}:{":".join(more_libraries)}', f'{mergerfs_path}'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, text=True)
    out, err = proc.communicate()
    if err:
        print(err)
        return -1

    # Download applist from Steam
    applist = os.path.join(cache_dir, 'applist.json')
    if not os.path.exists(applist):
        url = 'https://api.steampowered.com/ISteamApps/GetAppList/v2/'
        res = requests.get(url, allow_redirects=True)
        open(applist, 'wb').write(res.content)

    if mountpoint is None:
        mountpoint = os.path.join(data_dir, 'SteamFuse')
    if not os.path.exists(mountpoint):
        os.mkdir(mountpoint)
    try:
        FUSE(SteamFuseRegex(mergerfs_path, applist), mountpoint=mountpoint, nothreads=True, foreground=True)
    except RuntimeError:
        pass

    proc = subprocess.Popen(
        ['fusermount', '-u', f'{mergerfs_path}'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, text=True)
    out, err = proc.communicate()
    if err:
        print(err)
        return -1


if __name__ == '__main__':
    if len(sys.argv) > 2:
        main(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1])
