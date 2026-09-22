# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
import tomllib

from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH).parent
APP_VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
datas = []
binaries = []
hiddenimports = []

for package in ("praatio",):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

# Parselmouth is a compiled extension module rather than a regular package, so
# it is discovered by Analysis from this explicit import instead of collect_all.
hiddenimports.append("parselmouth")

datas.append((str(ROOT / "src" / "praatfigure" / "presets"), "praatfigure/presets"))

a = Analysis(
    [str(ROOT / "packaging" / "entrypoint.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PraatFigure",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
app_files = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="PraatFigure",
)

if sys.platform == "darwin":
    app = BUNDLE(
        app_files,
        name="PraatFigure.app",
        bundle_identifier="org.praatfigure.app",
        info_plist={
            "CFBundleDisplayName": "PraatFigure",
            "CFBundleName": "PraatFigure",
            "CFBundleShortVersionString": APP_VERSION,
            "NSHighResolutionCapable": True,
        },
    )
