# SMALauncher
A simple launcher/updater for [Shang Mu Architect](https://github.com/whitelilydragon/ShangMuArchitect).

Uses the following packages:
- `pyinstaller`
- `rqeuests`
- `tqdm`

## Building

Simply run `pyinstaller -F main.py -i icon.ico`!  
Your file should be in `dist/main.exe`.

You can optionally add [UPX](https://upx.github.io/) to your PATH to create smaller EXEs.
