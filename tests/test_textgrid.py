from pathlib import Path

from praatfigure.io.textgrid import load_textgrid


FIXTURE = Path(__file__).parent / "fixtures" / "sample.TextGrid"


def test_interval_and_point_tiers_unicode_and_nonzero_origin():
    grid = load_textgrid(FIXTURE)
    assert (grid.xmin, grid.xmax) == (1.0, 2.0)
    assert [tier.kind for tier in grid.tiers] == ["interval", "point"]
    assert grid.tier("phones").entries[1].label == "ə"
    assert grid.tier("phones").entries[2].label == 'a"b'
    assert grid.tier("events").entries[0].end is None


def test_search_modes_and_containing_interval():
    tier = load_textgrid(FIXTURE).tier("phones")
    assert [entry.label for entry in tier.search("Ə", "exact")] == ["ə"]
    assert [entry.label for entry in tier.search(r"^[aə]", "regex")] == ["ə", 'a"b']
    assert tier.containing(1.3).label == "ə"

