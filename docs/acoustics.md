# Acoustic analysis

## Waveform

Stereo audio is shown as a separate trace for each channel by default. The
waveform shares its time axis with every other track.

## Spectrogram

PraatFigure uses a broadband spectrogram and Praat-compatible computation when
Parselmouth is available. Frequency ticks in hertz are shown by default.
Spectrogram pixels use the selected DPI, while text, frames, and lines remain
vector elements in SVG and PDF exports.

## Pitch and formants

**Pitch** and **Formants** add analysis results over the spectrogram. Marker and
line sizes use physical Matplotlib units, so their proportions remain consistent
in Fit to window, Real size, and exported figures.

Analysis is limited to the displayed time window and cached. This keeps long
recordings responsive without reading the entire file after every style change.

