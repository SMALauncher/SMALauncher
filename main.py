import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime
from sys import exit

import requests
from tqdm import tqdm

local_meta_name = 'meta.json'
repo_path = 'whitelilydragon/ShangMuArchitect'
latest_release_url = 'https://api.github.com/repos/{0}/releases/latest'.format(repo_path)


def load_json(name):
    if not os.path.isfile(name):
        return None
    fp = open(name)
    obj = json.load(fp)
    fp.close()
    return obj


def try_update(local_meta):
    print('Fetching latest release from "{0}"'.format(latest_release_url))
    res = requests.get(latest_release_url, headers={'Accept': 'application/vnd.github.v3+json'})
    if res.status_code != 200:
        print('Failed to fetch latest release! Got status code {0}'.format(res.status_code))
        return local_meta
    latest_json = res.json()
    latest_id = int(latest_json['id'])
    latest_name = str(latest_json['tag_name'])
    if local_meta is None:
        print('First run!')
    else:
        current_id = int(local_meta['release_id'])
        current_name = str(local_meta['release_name'])
        if latest_id > current_id:
            print('We\'re out of date! Our version is {0}, while latest is {1}'.format(current_name, latest_name))
        else:
            print('We\'re up to date, yay!')
            return True, local_meta
    print('Downloading latest version {0}'.format(latest_name))
    # find meta.json first
    latest_meta_dl = None
    for asset in latest_json['assets']:
        if str(asset['name']) == 'meta.json':
            latest_meta_dl = str(asset['browser_download_url'])
            break
    if latest_meta_dl is None:
        print('Latest release is missing a "meta.json" asset! Please contact Libbie.')
        return False, local_meta
    res = requests.get(latest_meta_dl)
    if res.status_code != 200:
        print('Failed to fetch latest release metadata from "{0}"! Got status code {1}'
              .format(latest_meta_dl, res.status_code))
        return False, local_meta
    latest_meta = res.json()
    zip_md5 = str(latest_meta['asset_md5']).lower()
    # download the game ZIP
    zip_dl = None
    for asset in latest_json['assets']:
        if str(asset['content_type']) == 'application/x-zip-compressed':
            zip_dl = str(asset['browser_download_url'])
            break
    if zip_dl is None:
        print('Latest release is missing a ZIP file asset! Please contact Libbie.')
        return False, local_meta
    print('Downloading latest game ZIP from "{0}"'.format(zip_dl))
    zip_name = zip_dl.split('/')[-1]
    tmp_name = tempfile.mktemp()
    tmp_file = open(tmp_name, 'w+b')
    res = requests.get(zip_dl, stream=True)
    total = int(res.headers.get('content-length', 0))
    with tqdm(desc=zip_name,
              total=total,
              unit='iB',
              unit_scale=True,
              unit_divisor=1024) as bar:
        for chunk in res.iter_content(chunk_size=1024):
            size = tmp_file.write(chunk)
            bar.update(size)
    tmp_file.close()
    print('Done downloading ZIP!')
    # verify MD5
    print('Verifying MD5 of downloaded ZIP...')
    tmp_file = open(tmp_name, 'r+b')
    hash_md5 = hashlib.md5()
    with tqdm(desc=zip_name + ':md5',
              total=total,
              unit='iB',
              unit_scale=True,
              unit_divisor=1024) as bar:
        for chunk in iter(lambda: tmp_file.read(1024), b""):
            hash_md5.update(chunk)
            bar.update(1024)
    tmp_file.close()
    zip_md5_actual = hash_md5.hexdigest().lower()
    if zip_md5_actual != zip_md5:
        print('Downloaded ZIP has incorrect MD5 hash! Should be {0}, but is {1}'.format(zip_md5, zip_md5_actual))
        os.remove(tmp_name)
        return False, local_meta
    print('Done verifying ZIP!')
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
    local_meta['_comment1'] = 'Generated by SMALauncher on {0}'\
        .format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
    local_meta['_comment2'] = 'Manually modifying this file may cause update checking to break!!!'
    local_meta['release_id'] = latest_id
    local_meta['release_name'] = latest_name
    local_meta['exe_name'] = latest_meta['exe_name']
    return True, local_meta


def main():
    local_meta = load_json(local_meta_name)
    success, local_meta = try_update(local_meta)
    if local_meta is None:
        print('First run failed! Please check your Internet connection.')
        input('Press Enter to exit...')
        exit(1)
        return
    with open(local_meta_name, 'wt') as fp:
        json.dump(local_meta, fp)
    exe_name = str(local_meta['exe_name'])
    print('Running the game!')
    os.chdir('game')
    os.spawnl(os.P_NOWAIT, exe_name, exe_name)
    if not success:
        input('Press Enter to exit...')
        exit(1)


if __name__ == '__main__':
    main()
