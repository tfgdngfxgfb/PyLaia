from pathlib import Path

import pytest
import yaml

from ci.build_torch315 import ninja_executable, print_build_errors


def test_native_ci_and_launchers_use_visual_studio_2022():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/build.yml").read_text())
    assert workflow["jobs"]["torch315-windows"]["runs-on"] == "windows-2022"
    assert workflow["jobs"]["language-model"]["runs-on"] == "windows-2022"
    for name in ("build-torch315.ps1", "build-language-model.ps1"):
        script = (root / "ci" / name).read_text(encoding="utf-8")
        assert "-version '[17.0,18.0)'" in script


def test_windows_ninja_uses_existing_exe_not_extensionless_path(tmp_path):
    program = tmp_path / "Scripts/ninja.exe"
    program.parent.mkdir()
    program.write_bytes(b"native executable")
    assert ninja_executable(tmp_path) == program.as_posix()
    assert ninja_executable(tmp_path).endswith("/ninja.exe")


def test_windows_ninja_does_not_accept_a_non_exe_launcher(tmp_path):
    program = tmp_path / "Scripts/ninja"
    program.parent.mkdir()
    program.write_text("not a native Windows executable", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="native Windows Ninja executable"):
        ninja_executable(tmp_path)


def test_build_error_summary_preserves_errors_not_environment(tmp_path, capsys):
    log = tmp_path / "build.log"
    log.write_text(
        "process environment dump\n"
        "UNRELATED_ENV=must-not-be-published\n"
        "  CMake Error at cmake/Build.cmake:12 (message):\n"
        "UNRELATED_ENV=must-not-be-published\n"
        "    Required build input is missing.\n"
        "\n"
        "  command --irrelevant-argument\n"
        "file.cpp(12): fatal error C1083: Cannot open include file\n"
        "\n",
        encoding="utf-8",
    )
    print_build_errors(log)
    output = capsys.readouterr().out
    assert "Required build input is missing" in output
    assert "fatal error C1083" in output
    assert "must-not-be-published" not in output


def test_build_error_summary_retains_preceding_os_failure(tmp_path, capsys):
    log = tmp_path / "build.log"
    log.write_text(
        "  The system cannot find the path specified.\n"
        "  CMake Error: Generator: build tool execution failed\n",
        encoding="utf-8",
    )
    print_build_errors(log)
    assert "The system cannot find the path specified" in capsys.readouterr().out


def test_build_error_summary_redacts_credentials(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PYLAIA_TEST_SECRET", "private-example-value")
    log = tmp_path / "build.log"
    log.write_text(
        "ERROR: private-example-value https://username:password@example.invalid/\n",
        encoding="utf-8",
    )
    print_build_errors(log)
    output = capsys.readouterr().out
    assert "private-example-value" not in output
    assert "username:password" not in output
    assert "[REDACTED]" in output
