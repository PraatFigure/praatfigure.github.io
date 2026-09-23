# Interface

## Top controls

- **Pitch** toggles pitch over the spectrogram.
- **Formants** toggles formant points.
- **Boundary lines** controls dashed target boundaries.
- **Duration** shows target duration independently from boundary lines and time
  labels.
- **Open project…** and **Save project…** restore or save a complete session.
- **Export…** opens the export settings.

Waveform and spectrogram visibility is controlled only in the track table, so
there are no duplicate Wave or Spec switches in the top bar.

## Annotation search

The result table shows index, label, start, end, and duration. Search modes are
**contains**, **exact**, and **regex**. The table grows with the control panel so
that multiple results remain visible.

## Time and context

**Left context** and **Right context** extend the view around the selected
annotation; both default to 0. **Time mode** controls displayed values:

- **Reset to zero** sets zero at the beginning of the view.
- **Original time** uses absolute recording time.
- **Zero at target** sets zero at the beginning of the selected target.

## Preview

**Fit to window** scales the complete publication figure uniformly to the
available preview area. **Real size** preserves its physical dimensions and
uses scroll bars when needed. Fonts, lines, pitch, and formants scale together,
so preview proportions match the exported result.

Use the **Zoom** slider below the preview, or hold **Ctrl** and turn the mouse
wheel over the figure, to magnify it from 25% to 400%. A value of 100% means
the fitted size in **Fit to window** mode and the physical size in **Real size**
mode. Right-click the preview to reset zoom or copy the complete figure.

The in-app **Help** menu provides a compact guide to common operations.

## Spectrogram controls

The appearance panel includes dynamic range, pre-emphasis, quiet-region
normalization, time step, and frequency step. Higher dynamic range reveals more
low-level energy. Smaller time and frequency steps increase detail. Changes are
applied to every visible spectrogram track and redraw the preview automatically.
The smoothing selector provides bicubic, bilinear, and raw nearest-neighbour
display; bicubic is the Praat-like default.
