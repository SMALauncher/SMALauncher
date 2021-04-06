import json
import urllib.request
import semver
import shutil
import tempfile
import hashlib
import zipfile
import os

meta_url = 'https://raw.githubusercontent.com/Leo40Git/SMALauncher/master/meta.json'  # TODO replace with "live" link


def get_json_local(name):
    if not os.path.isfile(name):
        return None
    fp = open(name)
    obj = json.load(fp)
    fp.close()
    return obj


def get_json_remote(url):
    with urllib.request.urlopen(url) as res:
        return json.loads(res.read())


def main():
    json_local = get_json_local('version.json')
    print('Downloading latest version metadata from "{0}"'.format(meta_url))
    json_remote = get_json_remote(meta_url)

    ver_remote = json_remote['latest_version']
    update = True
    if (json_local is not None) and hasattr(json_local, 'version'):
        ver_local = json_local['version']
        update = semver.compare(ver_local, ver_remote) < 0
        if update:
            print('We\'re out of date! Our version is "{0}", while latest is "{1}"'.format(ver_local, ver_remote))
        else:
            print('We\'re up to date, yay!')
    else:
        print('First run! Downloading latest version "{0}"'.format(ver_remote))

    if update:
        dl_url = json_remote['download_url']
        print('Downloading latest version from "{0}"'.format(dl_url))
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        with urllib.request.urlopen(dl_url) as res:
            shutil.copyfileobj(res, tmp_file)

        tmp_file.seek(0)
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: tmp_file.read(4096), b""):
            hash_md5.update(chunk)
        md5_actual = hash_md5.hexdigest().lower()
        md5_expected = str(json_remote['download_md5']).lower()
        if md5_actual != md5_expected:
            print('ERROR: Downloaded file has bad MD5 hash! Expected "{0}", got "{0}"'.format(md5_expected, md5_actual))
            tmp_file.close()
            os.remove(tmp_file.name)
            exit(1)
        tmp_file.close()

        if os.path.isdir('game'):
            if os.path.isfile('gamedata_backup.dat'):
                os.remove('gamedata_backup.dat')
            os.rename('game/gamedata.dat', 'gamedata_backup.dat')

        print('Unzipping new version...')
        with zipfile.ZipFile(tmp_file.name, 'r') as zip_file:
            zip_file.extractall('game')

        if os.path.isfile('gamedata_backup.dat'):
            if os.path.isfile('game/gamedata.dat'):
                os.remove('game/gamedata.dat')
            os.rename('gamedata_backup.dat', 'game/gamedata.dat')

        os.remove(tmp_file.name)

        if json_local is None:
            json_local = {}
        json_local['version'] = ver_remote
        json_local['exe_name'] = json_remote['exe_name']
        with open('version.json', 'wt') as meta_file:
            json.dump(json_local, meta_file)

    os.system(json_local['exe_name'])


if __name__ == '__main__':
    main()
