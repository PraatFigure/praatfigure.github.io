# Troubleshooting

## `DLL load failed while importing QtCore`

Create a clean project-local environment and run PraatFigure from it:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[all]"
.\run_praatfigure.ps1
```

Deactivate Conda before launching the app. The ready-made Windows installer
contains a matching Qt runtime and does not require a system Python installation.

## A large audio file takes too long to open

PraatFigure initially reads only metadata and later loads the selected region.
Open the TextGrid and choose a short annotation first. Before a selection is
made, the initial preview is limited to ten seconds.

## Preview stops updating after export

Export is rendered in an independent figure and should not close the live
preview. If the issue recurs, save the project and attach its `.praatfig.json`,
operating-system version, and reproduction steps to a GitHub issue.

## A downloaded application does not start

Verify that the file came from the official Releases page. Unsigned packages
may be stopped by SmartScreen or Gatekeeper; see [Installation](installation.md)
for first-launch guidance. If a library is reported missing, use the complete
installer or AppImage rather than copying a single executable from a PyInstaller
folder.

