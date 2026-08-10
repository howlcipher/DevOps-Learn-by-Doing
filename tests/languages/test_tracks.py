import pytest

from devops_learn.domain.enums import LanguageTrackKind
from devops_learn.errors import ComingSoonError
from devops_learn.languages.go.track import GoTrack
from devops_learn.languages.python.track import PythonTrack


def test_python_track_is_available_and_describes_the_demo_app() -> None:
    track = PythonTrack()
    assert track.is_available is True
    assert track.kind == LanguageTrackKind.PYTHON
    assert "GET /health" in track.demo_app_endpoints()
    assert track.demo_app_summary()


def test_go_track_declares_itself_unavailable_and_raises_coming_soon() -> None:
    track = GoTrack()
    assert track.is_available is False
    assert track.kind == LanguageTrackKind.GO
    with pytest.raises(ComingSoonError):
        track.demo_app_summary()
    with pytest.raises(ComingSoonError):
        track.demo_app_endpoints()
