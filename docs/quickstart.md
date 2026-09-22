# Quick start

1. Select **Open audio…** and choose a recording.
2. Select **Open TextGrid…** and choose its annotation file.
3. Under **Find segment**, choose a tier and optionally filter its annotations.
4. Double-click an interval, or select it and press **Render selected interval**.
5. Configure tracks, labels, and appearance in the left panel.
6. Select **Export…**, check the filename, format, and folder, and save the image.

## Show the boundaries of an inner segment

Suppose the full word is on tier `word`, while only vowel `a` from tier
`segment` should be highlighted:

1. render the word from the `word` results table;
2. choose `segment` under **Target boundaries inside the view**;
3. check the row containing `a`;
4. enable **Boundary lines** if the dashed lines are required;
5. optionally enable endpoint labels or **Duration**.

Each inner interval has an independent checkbox. Uncheck it to remove its
projection. **Clear projected boundaries** clears the complete target selection.

## Use an arbitrary time range

Enter absolute values in **Start [s]** and **End [s]**, then select
**Use manual timespan**. The default export name for a manual selection contains
the absolute time range.

