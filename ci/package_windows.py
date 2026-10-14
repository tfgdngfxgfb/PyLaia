"""Assemble a Windows bundle with isolated Python runtimes and local LM wheels."""

import hashlib
import json
import shutil
import subprocess
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    version = project["version"]
    name = f"PyLaia-{version.replace('+', '-')}-Windows-x64"
    destination = ROOT / "dist" / name
    if destination.exists():
        raise RuntimeError(f"Build folder already exists: {destination}")
    destination.mkdir(parents=True)
    wheel_name = f"pylaia-{version}-py3-none-any.whl"
    (destination / "wheels").mkdir()
    shutil.copy2(ROOT / "dist" / wheel_name, destination / "wheels" / wheel_name)
    for tag in ("cp313", "cp314", "cp315"):
        source = ROOT / "dist/language-model" / tag
        wheels = destination / "wheels" / tag
        wheels.mkdir()
        for package, package_version in (
            ("kenlm", "0.3.0"),
            ("flashlight_text", "0.0.7"),
        ):
            filename = f"{package}-{package_version}+pylaia1-{tag}-{tag}-win_amd64.whl"
            shutil.copy2(source / filename, wheels / filename)
        if tag == "cp315":
            for filename in (
                "python_bidi-0.6.11-cp315-cp315-win_amd64.whl",
                "pyyaml-6.0.3-cp315-cp315-win_amd64.whl",
            ):
                shutil.copy2(source / filename, wheels / filename)
        shutil.copytree(source / "sources", destination / "sources" / tag)
    python_versions = {}
    for version_tag in ("313", "314", "315"):
        runtime = ROOT / ".runtime" / f"python{version_tag}"
        python_versions[f"3.{version_tag[1:]}"] = (
            subprocess.check_output(
                [str(runtime / "python.exe"), "--version"], text=True
            )
            .strip()
            .removeprefix("Python ")
        )
        shutil.copytree(
            runtime,
            destination / "runtime" / f"python{version_tag}",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for source, target in (
        ("ci/install-windows.ps1", "Install-PyLaia.ps1"),
        ("ci/verify_installation.py", "verify-installation.py"),
        ("ci/build_language_model.py", "build-tools/build_language_model.py"),
        ("ci/build-language-model.ps1", "build-tools/build-language-model.ps1"),
        ("ci/WINDOWS_BUILD_README.txt", "LES-MEG.txt"),
        ("LICENSE", "LICENSE-PyLaia.txt"),
        ("LICENSE-TORCHAUDIO", "LICENSE-TORCHAUDIO"),
        ("SECURITY.md", "SECURITY.md"),
        ("README.md", "README.md"),
    ):
        target_path = destination / target
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source, target_path)
    manifest = {
        "product": "PyLaia",
        "distribution": project["name"],
        "version": version,
        "pylaia_wheel": wheel_name,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "python": python_versions,
        "windows_support": {
            "3.13": ["CPU", "CUDA"],
            "3.14": ["CPU", "CUDA"],
            "3.15": ["CPU"],
        },
        "windows315_distributed_supported": False,
        "requires_network_for_other_dependencies": True,
        "files": [],
    }
    for path in sorted(destination.rglob("*")):
        if path.is_file():
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            manifest["files"].append(
                {"path": path.relative_to(destination).as_posix(), "sha256": digest}
            )
    (destination / "build-info.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    archive = ROOT / "dist" / f"{name}.zip"
    if archive.exists():
        raise RuntimeError(f"Build archive already exists: {archive}")
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as output:
        for path in sorted(destination.rglob("*")):
            if path.is_file():
                output.write(path, Path(name) / path.relative_to(destination))
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    with zipfile.ZipFile(archive) as output:
        if output.testzip() is not None:
            raise RuntimeError("Archive verification failed")
    print(f"{archive}\n{archive.stat().st_size / 1024**2:.1f} MiB\nSHA256 {digest}")


if __name__ == "__main__":
    main()
