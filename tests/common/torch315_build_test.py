from ci.build_torch315 import print_build_errors


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
    assert "irrelevant-argument" not in output


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
