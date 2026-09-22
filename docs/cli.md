# Command line

After installation, `praatfigure` without a subcommand opens the GUI.

## Render one example

```bash
praatfigure render \
  --audio example.wav \
  --textgrid example.TextGrid \
  --tier phones \
  --label "ə" \
  --padding-left 0.1 \
  --padding-right 0.1 \
  --output figure.svg
```

## Batch rendering

```bash
praatfigure batch \
  --audio example.wav \
  --textgrid example.TextGrid \
  --tier phones \
  --regex "^[aeiouə]$" \
  --output-dir figures
```

## Render a saved project

```bash
praatfigure render-project example.praatfig.json --output figure.pdf
```

Add `--overwrite` when an existing output file may be replaced. Run
`praatfigure --help` or, for example, `praatfigure render --help` for the full
current argument list.

