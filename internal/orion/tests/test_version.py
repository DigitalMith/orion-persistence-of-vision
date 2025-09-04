from orion import __version__
from orion.version import get_version


def test_version_matches():
    assert __version__ == "2.0.11"
    assert get_version() == "2.0.11"
