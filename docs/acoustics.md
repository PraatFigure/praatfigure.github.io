# Acoustic analysis

## Waveform

Stereo audio is shown as a separate trace for each channel by default. The
waveform shares its time axis with every other track.

## Spectrogram

PraatFigure uses a broadband spectrogram and Praat-compatible computation when
Parselmouth is available. The publication defaults use a 1 ms time step and a
10 Hz requested frequency step. Analysis extends slightly beyond the displayed
selection, then is cropped precisely to the frame, so no blank strip appears
between the spectrogram image and its border.

The interface exposes the main display controls:

- **Dynamic range** controls how much low-level detail and background noise is
  retained. A larger value shows weaker energy.
- **Pre-emphasis from** applies a Praat-like 6 dB/octave display emphasis above
  the selected frequency. The default is 50 Hz; set it to **Off** to disable it.
- **Quiet-region normalization** ranges from 0 to 1 and defaults to 0.25. Higher
  values raise quiet time slices relative to loud ones, making weak segments and
  noise more visible.
- **Time step** and **Frequency step** control analysis-grid detail. Smaller
  values produce more cells but require more computation.

These operations affect visualization only; the source audio is never modified.
Frequency ticks in hertz are shown by default. Spectrogram pixels use the
selected export DPI, while text, frames, and lines remain vector elements in
SVG and PDF exports.

## Pitch and formants

**Pitch** and **Formants** add analysis results over the spectrogram. Marker and
line sizes use physical Matplotlib units, so their proportions remain consistent
in Fit to window, Real size, and exported figures.

Analysis is limited to the displayed time window and cached. This keeps long
recordings responsive without reading the entire file after every style change.
