from importlib.metadata import distribution, version

from laia import *


def test_wildcard_import():
    # these are defined in __all__
    assert __version__
    assert __root__
    assert get_installed_versions


def test_independent_build_identity():
    assert "+fork." in version("pylaia")
    assert any(v.startswith("pylaia==") for v in get_installed_versions())


def test_original_package_and_command_names():
    package = distribution("pylaia")
    assert package.metadata["Name"] == "pylaia"
    assert {
        entry.name for entry in package.entry_points if entry.group == "console_scripts"
    } == {
        "pylaia-htr-create-model",
        "pylaia-htr-decode-ctc",
        "pylaia-htr-netout",
        "pylaia-htr-train-ctc",
        "pylaia-htr-dataset-validate",
    }
