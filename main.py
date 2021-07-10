import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime
from enum import Enum
from sys import exit, argv
from typing import Optional, AnyStr

import requests
from tqdm import tqdm

version = '1.3.0'

local_meta_name = 'meta.json'
repo_path = 'whitelilydragon/ShangMuArchitect'
repo_path_rolling = 'SMALauncher/SMARolling'
latest_release_url_template = 'https://api.github.com/repos/{}/releases/latest'

if ('--help' in argv) or ('-?' in argv):
    print('SMALauncher v{}'.format(version))
    print('A simple launcher/updater for Shang Mu Architect. Updates your game while keeping your settings intact!')
    print()
    print('Usage:')
    print('\t{} [--help/-?] [--rolling/-R]'.format(argv[0]))
    print()
    print('\t--help/-?\t- displays this help message and exists')
    print('\t--rolling/-R\t- enables updating to rolling versions of SMA')
    exit(0)


def load_json(name: str) -> Optional[dict]:
    if not os.path.isfile(name):
        return None
    try:
        with open(name) as f:
            obj = json.load(f)
    except EnvironmentError as err:
        print('Failed to read JSON file: {}'.format(err))
        obj = None
    return obj


class UpdateResult(Enum):
    FAIL = -1,
    UP_TO_DATE = 0,
    SUCCESS = 1


def content_type_is_zip(content_type: AnyStr) -> bool:
    return (content_type == 'application/zip') or (content_type == 'application/x-zip-compressed')


def update(rolling: bool, local_meta: Optional[dict]) -> tuple[UpdateResult, Optional[dict]]:
    if rolling:
        print('Checking for rolling releases...')
        latest_release_url = latest_release_url_template.format(repo_path_rolling)
    else:
        print('Checking for stable releases...')
        latest_release_url = latest_release_url_template.format(repo_path)
    print('Fetching latest release from "{}"'.format(latest_release_url))
    res = requests.get(latest_release_url, headers={'Accept': 'application/vnd.github.v3+json'})
    if res.status_code != 200:
        print('Failed to fetch latest release! Got status code {}'.format(res.status_code))
        return UpdateResult.FAIL, local_meta
    latest_json = res.json()
    latest_id = int(latest_json['id'])
    latest_name = str(latest_json['tag_name'])
    if local_meta is None:
        print('First run!')
    else:
        current_id = int(local_meta['release_id'])
        current_name = str(local_meta['release_name'])
        if latest_id > current_id:
            print('We\'re out of date! Our version is {}, while latest is {}'.format(current_name, latest_name))
        else:
            print('We\'re up to date, yay!')
            return UpdateResult.UP_TO_DATE, local_meta
    print('Downloading latest version {}'.format(latest_name))
    # find meta.json first
    latest_meta_dl = None
    for asset in latest_json['assets']:
        if str(asset['name']) == 'meta.json':
            latest_meta_dl = str(asset['browser_download_url'])
            break
    if latest_meta_dl is None:
        print('Latest release "{}" is missing a "meta.json" asset! Please contact Libbie.'
              .format(latest_name))
        return UpdateResult.FAIL, local_meta
    res = requests.get(latest_meta_dl)
    if res.status_code != 200:
        print('Failed to fetch latest release metadata from "{}"! Got status code {}'
              .format(latest_meta_dl, res.status_code))
        return UpdateResult.FAIL, local_meta
    latest_meta = res.json()
    zip_md5 = str(latest_meta['asset_md5']).lower()
    # download the game ZIP
    zip_dl = None
    for asset in latest_json['assets']:
        if str(asset['name']).startswith('Shang_Mu_Architect_') \
                and content_type_is_zip(str(asset['content_type'])):
            zip_dl = str(asset['browser_download_url'])
            break
    if zip_dl is None:
        print('Latest release "{}" is missing the game ZIP file (name starts with "Shang_Mu_Architect_")!'
              'Please contact Libbie.'.format(latest_name))
        return UpdateResult.FAIL, local_meta
    print('Downloading latest game ZIP from "{}"'.format(zip_dl))
    zip_name = zip_dl.split('/')[-1]
    tmp_name = tempfile.mktemp()
    res = requests.get(zip_dl, stream=True)
    total = int(res.headers.get('content-length', 0))
    try:
        with open(tmp_name, 'w+b') as tmp_file, \
                tqdm(desc=zip_name,
                     total=total,
                     unit='iB',
                     unit_scale=True,
                     unit_divisor=1024) as bar:
            for chunk in res.iter_content(chunk_size=1024):
                size = tmp_file.write(chunk)
                bar.update(size)
    except KeyboardInterrupt:
        print('Interrupted by user, aborting')
        os.remove(tmp_name)
        return UpdateResult.FAIL, local_meta
    print('Done downloading ZIP!')
    # verify MD5
    print('Verifying MD5 of downloaded ZIP...')
    hash_md5 = hashlib.md5()
    try:
        with open(tmp_name, 'r+b') as tmp_file:
            for chunk in iter(lambda: tmp_file.read(1024), b""):
                hash_md5.update(chunk)
    except KeyboardInterrupt:
        print('Interrupted by user, aborting')
        os.remove(tmp_name)
        return UpdateResult.FAIL, local_meta
    zip_md5_actual = hash_md5.hexdigest().lower()
    if zip_md5_actual != zip_md5:
        print('Downloaded ZIP has incorrect MD5 hash! Should be {}, but is {}'.format(zip_md5, zip_md5_actual))
        os.remove(tmp_name)
        return UpdateResult.FAIL, local_meta
    print('ZIP verified! Download was successful!')
    # back up gamedata.dat (settings, best times)
    if os.path.isdir('game'):
        if os.path.isfile('gamedata_backup.dat'):
            os.remove('gamedata_backup.dat')
        os.rename('game/gamedata.dat', 'gamedata_backup.dat')
    # unzip
    print('Unzipping to "game" folder..')
    with zipfile.ZipFile(tmp_name, 'r') as zip_file:
        zip_file.extractall('game')
    os.remove(tmp_name)
    # restore gamedata.dat
    if os.path.isfile('gamedata_backup.dat'):
        if os.path.isfile('game/gamedata.dat'):
            os.remove('game/gamedata.dat')
        os.rename('gamedata_backup.dat', 'game/gamedata.dat')
    # update local meta
    if local_meta is None:
        local_meta = {}
    local_meta['_comment1'] = 'Generated by SMALauncher on {}' \
        .format(datetime.now().strftime("%Y/%m/%d, %H:%M:%S"))
    local_meta['_comment2'] = 'Manually modifying this file may cause update checking to break!!!'
    local_meta['release_id'] = latest_id
    local_meta['release_name'] = latest_name
    local_meta['exe_name'] = latest_meta['exe_name']
    return UpdateResult.SUCCESS, local_meta


def try_update(rolling: bool, local_meta: Optional[dict]) -> tuple[UpdateResult, Optional[dict]]:
    try:
        return update(rolling, local_meta)
    except Exception as err:
        print('Failed to update game due to exception:\n'
              '  {}: {}'.format(type(err).__name__, str(err)))
        return UpdateResult.FAIL, local_meta


def main():
    local_meta = None
    if os.path.isdir('game'):
        local_meta = load_json(local_meta_name)
        if local_meta is None:
            # game is probably unrelated, then
            name = 'game_unrelated_{}'.format(datetime.now().strftime('%Y%m%dT%H%M%S'))
            try:
                os.rename('game', name)
                print('Found unrelated "game" directory, has been renamed to "{}"'.format(name))
            except EnvironmentError as err:
                print('Found unrelated "game" directory and couldn\'t rename it, crashing instead\n'
                      '  {}: {}'.format(type(err).__name__, str(err)))
                exit(1)
                return
    rolling = ('--rolling' in argv) or ('-R' in argv)
    result, local_meta = try_update(rolling, local_meta)
    if result == UpdateResult.UP_TO_DATE and rolling:
        result, local_meta = try_update(False, local_meta)
    if local_meta is None:
        print('First run failed! Please check your Internet connection.')
        input('Press Enter to exit... ')
        exit(1)
        return
    with open(local_meta_name, 'wt') as fp:
        json.dump(local_meta, fp)
    if result == UpdateResult.FAIL:
        print('Failed to update game.')
        answer = input('Launch anyways? [Y/n] ').lower().strip()[:1]
        if answer == 'n':
            exit(0)
            return
    exe_name = str(local_meta['exe_name'])
    print('Running the game!')
    os.chdir('game')
    os.spawnl(os.P_NOWAIT, exe_name, exe_name)
    if result == UpdateResult.FAIL:
        input('Press Enter to exit...')
        exit(1)


if __name__ == '__main__':
    main()
