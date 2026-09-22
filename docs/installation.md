# Installation

## Ready-to-use applications

Open the repository's **Releases** page and download the package for your
operating system.

### Windows

Run `PraatFigure-…-Windows-x64-Setup.exe`. The installer adds PraatFigure to the
Start menu and can create a desktop shortcut.

Automated builds are currently unsigned. Windows SmartScreen may therefore
display a warning for a new version. Verify that the file came from the
official PraatFigure Releases page.

### macOS

Open the DMG for your architecture and move PraatFigure to Applications:

- `macOS-arm64` for Apple Silicon (M1 or newer);
- `macOS-x86_64` for Intel Macs.

The app is not yet notarized by Apple. Its first launch may require approval in
**System Settings → Privacy & Security**.

### Linux

Make the AppImage executable and run it:

```bash
chmod +x PraatFigure-*-Linux-x86_64.AppImage
./PraatFigure-*-Linux-x86_64.AppImage
```

Each release also contains a portable `.tar.gz`. Extract it and run
`PraatFigure/PraatFigure`.

## Install from source

Python 3.12 is required.

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[all]"
.\run_praatfigure.ps1
```

macOS and Linux:

```bash
source .venv/bin/activate
python -m pip install -e ".[all]"
praatfigure
```

A project-local virtual environment is especially useful on Windows because it
isolates Qt from incompatible DLLs placed on `PATH` by Conda or other software.

