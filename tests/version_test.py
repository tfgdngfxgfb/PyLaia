from importlib.metadata import distribution, version
from pathlib import Path

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


@pytest.mark.parametrize("python", ["3.14", "3.15"])
def test_supported_python_versions(python):
    supported = SpecifierSet(distribution("pylaia").metadata["Requires-Python"])
    assert python in supported
    assert "3.12" not in supported
    assert "3.13" not in supported
    assert "3.16" not in supported


@pytest.mark.parametrize("python", ["3.14", "3.15"])
def test_torchaudio_is_only_required_on_older_python(python):
    audio = next(
        Requirement(item)
        for item in distribution("pylaia").requires
        if Requirement(item).name == "torchaudio"
    )
    assert audio.marker.evaluate(
        {"python_version": python, "extra": "language-model"}
    ) == (python != "3.15")


def test_python313_is_not_advertised_or_bundled():
    import yaml

    package = distribution("pylaia")
    assert "Programming Language :: Python :: 3.13" not in package.metadata.get_all(
        "Classifier", []
    )
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/build.yml").read_text())
    for job in ("test", "language-model"):
        assert workflow["jobs"][job]["strategy"]["matrix"]["python"] == ["3.14", "3.15"]
    installer = (root / "ci/install-windows.ps1").read_text()
    assert "[ValidateSet('3.14', '3.15')]" in installer
    packager = (root / "ci/package_windows.py").read_text()
    assert '"cp313"' not in packager
    assert '"313"' not in packager
    assert '"3.13"' not in packager


@pytest.mark.parametrize(
    "name,expected",
    [
        ("pillow", "13.0.0"),
        ("filelock", "4.2.4"),
        ("python-bidi", "0.6.12"),
        ("setuptools", "84.2.1"),
        ("jsonargparse", "4.53.0"),
        ("mpmath", "1.4.1"),
        ("sympy", "1.14.0+pylaia1"),
    ],
)
def test_runtime_dependency_versions_are_pinned(name, expected):
    requirement = next(
        Requirement(item)
        for item in distribution("pylaia").requires
        if Requirement(item).name.lower() == name
    )
    assert str(requirement.specifier) == f"=={expected}"
    assert version(name) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("cachetools", "7.2.7"),
        ("distlib", "0.4.4"),
        ("platformdirs", "4.14.0"),
        ("pluggy", "1.7.0"),
        ("pyproject-api", "1.12.2"),
        ("python-discovery", "1.6.7"),
        ("virtualenv", "21.15.1"),
        ("tox", "4.67.4"),
        ("pytest", "9.2.0"),
        ("pip", "26.2.2"),
        ("markdown", "3.11.2"),
        ("certifi", "2026.10.23"),
        ("xxhash", "4.0.2"),
        ("wcwidth", "0.9.4"),
    ],
)
def test_tool_dependency_versions_are_pinned(name, expected):
    requirement = next(
        Requirement(item)
        for item in distribution("pylaia").requires
        if Requirement(item).name.lower() == name
    )
    assert str(requirement.specifier) == f"=={expected}"
    assert requirement.marker.evaluate({"extra": "test"})
    assert not requirement.marker.evaluate({"extra": ""})
    assert version(name) == expected


def test_cwevals_version_matches_the_local_wandb_requirement():
    requirement = next(
        Requirement(item)
        for item in distribution("pylaia").requires
        if Requirement(item).name.lower() == "cwevals"
    )
    assert str(requirement.specifier) == "==0.0.1b3"
    assert requirement.marker.evaluate({"extra": "wandb"})
    assert not requirement.marker.evaluate({"extra": ""})
