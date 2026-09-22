import numpy as np
import pytest

from praatfigure.models.selection import Target, TimeRange, TimeTransform


def test_padding_is_clamped():
    assert TimeRange(1.0, 2.0).padded(0.5, 0.5, minimum=0.8, maximum=2.2) == TimeRange(0.8, 2.2)


@pytest.mark.parametrize(
    "mode,expected",
    [("absolute", [1.0, 1.25]), ("relative_to_view_start", [0.0, 0.25]),
     ("relative_to_target_start", [-0.1, 0.15])],
)
def test_time_transform(mode, expected):
    transform = TimeTransform(mode, view_start=1.0, target_start=1.1)
    np.testing.assert_allclose(transform.forward(np.array([1.0, 1.25])), expected)
    np.testing.assert_allclose(transform.inverse(np.array(expected)), [1.0, 1.25])


def test_invalid_ranges_rejected():
    with pytest.raises(ValueError):
        TimeRange(2, 1)
    with pytest.raises(ValueError):
        Target(1, 1)

