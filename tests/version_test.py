from importlib.metadata import version

from laia import *


def test_wildcard_import():
    # these are defined in __all__
    assert __version__
    assert __root__
    assert get_installed_versions


def test_independent_build_identity():
    assert "+fork." in version("pylaia-fork")
    assert any(v.startswith("pylaia-fork==") for v in get_installed_versions())
