from importlib.metadata import distribution, version

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

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


@pytest.mark.parametrize("python", ["3.13", "3.14", "3.15"])
def test_supported_python_versions(python):
    supported = SpecifierSet(distribution("pylaia").metadata["Requires-Python"])
    assert python in supported
    assert "3.12" not in supported
    assert "3.16" not in supported


@pytest.mark.parametrize("python", ["3.13", "3.14", "3.15"])
def test_torchaudio_is_only_required_on_older_python(python):
    audio = next(
        Requirement(item)
        for item in distribution("pylaia").requires
        if Requirement(item).name == "torchaudio"
    )
    assert audio.marker.evaluate(
        {"python_version": python, "extra": "language-model"}
    ) == (python != "3.15")
