# Export, templates, and projects

## Export

The **Export…** dialog provides:

- output folder and filename;
- PNG, SVG, or PDF format;
- output DPI;
- transparent PNG background.

PNG is selected by default. For an annotation-based view, the default filename
starts with its Unicode label. A manual view uses its absolute time range.
Existing files are not overwritten without confirmation.

For quick use in another application, press **Copy PNG (300 DPI)** below the
preview or right-click the preview and choose **Copy figure as PNG (300 DPI)**.
PraatFigure renders a fresh full-resolution image rather than copying the
possibly scaled on-screen preview.

SVG and PDF are ideal for publications because text and lines remain vector
elements. PNG is convenient for slides, websites, and software that does not
support vector graphics.

## Templates

**Templates → Save settings template…** stores appearance, tracks, order,
heights, labels, fonts, and analysis parameters. It does not store the current
audio file or time selection, so one style can be reused across examples.

## Projects

A `.praatfig.json` project stores audio and TextGrid paths, the current
selection, and the complete figure specification. Moving a project to another
computer may require updating its source-file paths.
