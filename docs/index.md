# PraatFigure

PraatFigure creates publication-ready phonetic figures from an audio recording
and a Praat TextGrid. Waveforms, spectrograms, annotation tiers, selected
boundaries, pitch, and formants are combined in one precisely configurable
figure.

## Features

- Open long recordings without loading the complete file into memory.
- Find TextGrid intervals by substring, exact match, or regular expression.
- Render an annotated interval or an arbitrary time range.
- Project only selected inner-segment boundaries onto waveform and spectrogram.
- Reorder, rename, hide, and resize every track.
- Control time ticks, axes, tier names, boundaries, endpoint labels, and duration
  independently.
- Select an installed system font and configure text sizes and boundary width.
- Preview with **Fit to window** or at physical **Real size**.
- Export Unicode-named PNG, SVG, and PDF files.
- Save complete projects and reusable appearance templates.
- Batch-render examples from the command line.

Waveform and spectrogram tracks default to relative height 1.0. Every TextGrid
track defaults to 0.5. Left and right context default to zero, the time axis
shows only its endpoints, and PNG is the default export format.

Continue with [Installation](installation.md) and the
[Quick start](quickstart.md).

