# SMALauncher
A simple launcher/updater for [Shang Mu Architect](https://github.com/whitelilydragon/ShangMuArchitect). Updates your game while keeping your settings intact!

You can download the latest release of the launcher [here](https://github.com/Leo40Git/SMALauncher/releases/latest).

Alternatively, you can download [the script](https://github.com/Leo40Git/SMALauncher/blob/master/main.py) and run it with Python 3 (Python 2 is untested). Take care to install the [necessary packages](#packages), though.

Simply download it into some directory and run it - it'll automatically download the latest release of the game and launch it!

No special actions are needed to update the game - the launcher will automatically check every time it's run.

## Packages

- `requests` - for easier interaction with the web
- `tqdm` - for some fancy loading bars!


## Building from source

Install the `pyinstaller`, then run `pyinstaller -F main.py -i icon.ico`.  
Your file should be in `dist/main.exe`.

You can optionally add [UPX](https://upx.github.io/) to your PATH to create smaller EXEs.
