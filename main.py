import json
import urllib.request
import semver
import shutil
import tempfile

meta_url = 'https://raw.githubusercontent.com/Leo40Git/SMALauncher/master/meta.json'  # TODO replace with "live" link


def get_json_local(name):
    fp = open(name)
    obj = json.load(fp)
    fp.close()
    return obj


def get_json_remote(url):
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())


if __name__ == '__main__':
    json_local = get_json_local('meta.json')
    json_remote = get_json_remote(meta_url)

    update = not hasattr(json_local, 'version')
    if not update:
        ver_local = json_local['version']
        ver_remote = json_remote['latest_version']
        update = semver.compare(ver_local, ver_remote) < 0

    if update:
        with urllib.request.urlopen(json_remote['download_url']) as response:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                shutil.copyfileobj(response, tmp_file)
        print('downloaded to "{0}"'.format(tmp_file.name))
