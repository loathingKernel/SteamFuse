import os
import sys
import requests
from fuse import FUSE
from xdg import BaseDirectory

from steamfuse_tree import SteamFuse


def main(steam_path=None, mountpoint=None):

    config_dir = BaseDirectory.save_config_path('steamfuse')
    data_dir = BaseDirectory.save_data_path('steamfuse')
    cache_dir = BaseDirectory.save_cache_path('steamfuse')

    applist = os.path.join(cache_dir, 'applist.json')
    if not os.path.exists(applist):
        url = 'https://api.steampowered.com/ISteamApps/GetAppList/v2/'
        res = requests.get(url, allow_redirects=True)
        open(applist, 'wb').write(res.content)

    if mountpoint is None:
        mountpoint = BaseDirectory.save_data_path('steamfuse')
    try:
        FUSE(SteamFuse(mountpoint, steam_path, applist),
             os.path.join(mountpoint, 'SteamFuse'), nothreads=True, foreground=True)
    except RuntimeError:
        pass


if __name__ == '__main__':
    if len(sys.argv) > 2:
        main(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1])
