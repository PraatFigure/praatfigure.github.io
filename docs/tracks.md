# Tracks and appearance

## Track table

The **Tracks** table lets you:

- toggle a track's visibility;
- edit the name printed on the figure;
- set its relative height;
- drag rows to change their order.

The figure redraws immediately after reordering. Dropping one row onto another
only changes its position; it does not remove either track.

Default heights:

| Track type | Height |
| --- | ---: |
| Waveform | 1.0 |
| Spectrogram | 1.0 |
| TextGrid tier | 0.5 |

Height is relative, so a 1.0 track is twice as tall as a 0.5 track. Newly added
TextGrid tracks use 0.5, while saved projects retain their explicit values.

## Axes and labels

The following can be configured independently:

- time ticks: endpoints, automatic, or hidden;
- the `Time [s]` axis label;
- waveform amplitude axis;
- spectrogram frequency ticks in hertz;
- tier names;
- target start and end values above the figure.

Annotation tracks always include their left and right frame boundaries. Figure
margins are recalculated to accommodate long custom track names.

## Fonts and sizes

The font picker lists families installed on the current system. Base,
annotation, and axis text sizes are configured separately. Axis text defaults
to 6 pt. Export uses physical point sizes, while the preview scales the complete
composition as one unit.

