# SteamFuse
FUSE filesystem for the Steam Library

This software is alpha stage, use at your own risk.


## Description

**SteamFuse** is a FUSE based filesystem for the Steam library. It translates the file names in
Steam Libraries from application IDs into application titles for easier browsing and manipulation.
It does this by providing a different view though FUSE without renaming the actual files.


## Features
* Translates applications IDs into game titles for `compatdata` and `.acf` files and folders.
* Unified view of all Steam libraries present in the system by using MergerFS.
* Supports some file operations and restricts others to avoid breaking the underlying file structure.


## Dependencies

### Software
* MergerFS

### Python modules
* vdf
* orjson
* requests
* pyxdg
* fusepy


## Installation
```shell
git clone https://github.com/loathingKernel/SteamFuse
```


## Usage

```shell
cd SteamFuse
python3 -m steamfuse
```
or
```shell
cd SteamFuse
python3 -m steamfuse <path_to_steam_folder> <path_to_mount_folder>
```


## License
