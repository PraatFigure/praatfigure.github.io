from praatfigure.models.figure import FigureSpec
from praatfigure.models.project import Project
from praatfigure.models.selection import Target, TimeRange
from praatfigure.models.tracks import AnnotationTrack


def test_project_round_trip(tmp_path):
    spec = FigureSpec.publication(TimeRange(1.0, 1.8), [Target(1.2, 1.4, "phones", 2, "ə")], ["phones"])
    project = Project("sound.wav", "sound.TextGrid", spec)
    path = tmp_path / "sample.praatfig.json"
    project.save(path)
    restored = Project.load(path)
    assert restored.to_dict() == project.to_dict()
    assert isinstance(restored.figure_spec.tracks[-1], AnnotationTrack)

