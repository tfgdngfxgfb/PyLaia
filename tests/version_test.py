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


def test_only_python315_is_supported():
    package = distribution("pylaia")
    supported = SpecifierSet(package.metadata["Requires-Python"])
    assert "3.15" in supported
    for unsupported in ("3.13", "3.14", "3.16"):
        assert unsupported not in supported
    assert not any(Requirement(item).name == "torchaudio" for item in package.requires)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("pillow", "13.0.0"),
        ("filelock", "4.2.9"),
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
        ("cachetools", "8.0.0"),
        ("distlib", "0.4.4"),
        ("platformdirs", "4.14.5"),
        ("pluggy", "1.7.0"),
        ("pyproject-api", "1.12.5"),
        ("python-discovery", "1.9.5"),
        ("virtualenv", "21.15.6"),
        ("tox", "4.67.13"),
        ("pytest", "9.2.0"),
        ("pip", "26.3"),
        ("markdown", "3.11.3"),
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
