# PraatFigure

PraatFigure turns an audio file plus a Praat TextGrid selection into a consistent,
publication-ready SVG, PDF, or PNG. The same declarative `FigureSpec` drives the
renderer, command-line interface, and desktop preview.

Full Russian-language documentation is maintained in [`docs/`](docs/index.md)
and published at [praatfigure.github.io](https://praatfigure.github.io/).

## Download

[GitHub Releases](https://github.com/PraatFigure/praatfigure.github.io/releases)
are built automatically for all supported systems:

- Windows x64 installer (`Setup.exe`);
- macOS applications for Apple Silicon and Intel (`.dmg`);
- Linux x86_64 AppImage and portable archive.

The packages are currently unsigned. See the
[installation guide](docs/installation.md) for the first-launch notes.

## Install and run

```powershell
python -m pip install -e ".[all]"
praatfigure
```

On Windows, a project-local virtual environment is recommended because Conda
and unrelated applications can place incompatible Qt/ICU DLLs on `PATH`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[all]"
.\run_praatfigure.ps1
```

The core renderer works with WAV files without optional dependencies. For the
desktop application and Praat-compatible pitch/formant analysis, install the
`all` extra shown above.

Audio is opened lazily: only metadata is read initially, and acoustic analysis
loads the selected time window rather than the whole recording. The first
preview is capped at 10 seconds until an annotation or manual range is chosen.

In the desktop interface, double-click an annotation (or use **Render selected
interval**) to define the view. Then choose another interval tier under
**Target boundaries inside the view**, select one or more contained annotations,
and press **Project selected boundaries**. Only those target boundaries are
projected through the waveform and spectrogram. Track checkboxes control
visibility; selecting a track exposes its relative height. Waveform and
spectrogram tracks default to height 1.0, while TextGrid annotation tracks
default to 0.5.

The **Templates** menu saves and restores visual settings without storing the
current time selection. The export dialog provides an editable Unicode filename,
SVG/PDF/PNG format, DPI, and PNG transparency. Annotation labels are used in the
default filename; manual selections use their absolute start-end interval.

Preview supports **Fit to window**, which scales the entire final composition
uniformly, and **Real size**, which displays its configured physical dimensions.
Font sizes, pitch/formant markers, and line widths therefore retain the same
proportions at every Windows display scale.

PNG is the default export format. The appearance panel exposes installed system
fonts and independent base, annotation, and axis sizes (axis defaults to 6 pt).
Duration rendering is independent from target boundary lines and start/end labels.

Render the first exact annotation match from the command line:

```powershell
praatfigure render --audio example.wav --textgrid example.TextGrid `
  --tier phones --label "ə" --padding-left 0.1 --padding-right 0.1 `
  --output figure.svg
```

Render every regex match:

```powershell
praatfigure batch --audio example.wav --textgrid example.TextGrid `
  --tier phones --regex "^[aeiouə]$" --output-dir figures --format png
```

Project files (`.praatfig.json`) contain paths, the current selection, and the
complete figure specification. They can be rendered reproducibly with:

```powershell
praatfigure render-project example.praatfig.json --output figure.pdf
```

## Current scope

This first working version includes IntervalTier and PointTier parsing, searchable
annotations, selection padding, three time-origin modes, waveform and broadband
spectrogram tracks, optional Praat pitch/formant overlays, annotation tracks,
boundary projection/deduplication, target highlighting/durations, presets,
project serialization, batch rendering, vector/raster export, and a basic live
desktop preview. The data and rendering layers do not depend on the GUI.

## Development and releases

```powershell
python -m pip install -e ".[all,dev,build,docs]"
python -m pytest -q
python -m mkdocs serve
pyinstaller --noconfirm --clean packaging/PraatFigure.spec
```

CI, platform-native installers, automatic tagged releases, and GitHub Pages are
defined in [`.github/workflows`](.github/workflows). Detailed maintainer steps
are in the [build and publication guide](docs/development.md).
