# Selecting a region and projecting boundaries

PraatFigure distinguishes two concepts:

**View**
: The complete time span of the figure. It comes from an annotation plus
  optional context, or from manually entered times.

**Target**
: One or more inner intervals whose boundaries or durations should be
  highlighted inside the view.

After choosing a view, **Target boundaries inside the view** lists intervals
from the selected tier that lie inside that window. Checking a row adds the
interval to the targets; unchecking it removes its projection.

## Independent display options

- **Boundary lines** draws vertical dashed boundaries.
- **Label target start/end above figure** prints endpoint times.
- **Duration** prints the interval duration.

These options can be used in any combination. Labels for very short targets are
pushed apart to avoid overlap. Dashed-line width is configurable separately.
Coincident target boundaries are merged with a small tolerance so the same line
is not drawn repeatedly.

