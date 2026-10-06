"""Build patched Windows wheels from hash-verified upstream source releases.

Run via build-language-model.ps1 to activate the MSVC compiler first. The
temporary build environment is separate from the target PyLaia environment.
"""

import argparse
import hashlib
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "kenlm-0.3.0": (
        "https://files.pythonhosted.org/packages/02/6e/f4e159cef39ea4ef2244b4aa32857d447d60a5d0ee269e1b1f8d3723c03e/kenlm-0.3.0.tar.gz",
        "c4628bb9fb63c8a6f9240035b8b037385cfc404cb72e933cf48878291edac1e8",
    ),
    "flashlight-text-0.0.7": (
        "https://files.pythonhosted.org/packages/3a/b8/83f5a6a5aae7acc9289acd0c1e9ef954ccb881a912019f7bbb35f7d3a4cb/flashlight-text-0.0.7.tar.gz",
        "fb63779b4b642c0c59e66386f43db8357836ed1be82b49d30155f7c39136d836",
    ),
}
BUILD_TOOLS = [
    "pip==26.2.1",
    "setuptools==84.0.0",
    "wheel==0.48.0",
    "packaging==26.3",
    "cmake==4.4.4",
    "ninja==1.13.2",
    "Cython==3.3.0",
    "pybind11==3.1.0",
]


def replace_source(path, old, new):
    """Apply an exact mechanical patch; fail rather than guess on source changes."""
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise RuntimeError(f"Unexpected upstream source: {path.name}")
    path.write_text(source.replace(old, new), encoding="utf-8", newline="\n")


def prepare_sources(directory):
    for name, (url, expected_hash) in SOURCES.items():
        archive = directory / f"{name}.tar.gz"
        urllib.request.urlretrieve(url, archive)
        with archive.open("rb") as stream:
            actual_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual_hash != expected_hash:
            raise RuntimeError(f"Source checksum mismatch: {name}")
        with tarfile.open(archive) as source:
            source.extractall(directory, filter="data")

    kenlm = directory / "kenlm-0.3.0"
    flashlight = directory / "flashlight-text-0.0.7"
    replace_source(kenlm / "setup.py", "version='0.3.0'", "version='0.3.0+pylaia1'")
    # The original Windows setup probes unavailable Unix tools unnecessarily.
    replace_source(
        kenlm / "setup.py",
        "def compile_test(header, library):\n",
        "def compile_test(header, library):\n"
        "    if platform.system() == 'Windows':\n        return False\n",
    )
    replace_source(
        kenlm / "util/file.cc",
        "namespace util {\n",
        "namespace util {\n"
        + r"""
#if defined(_WIN32) || defined(_WIN64)
static std::wstring Utf8FileName(const char *name) {
  const int size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, name, -1, NULL, 0);
  if (size == 0) throw std::runtime_error("Invalid UTF-8 filename");
  std::wstring path(size, L'\0');
  if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, name, -1, &path[0], size) == 0)
    throw std::runtime_error("Invalid UTF-8 filename");
  return path;
}
#endif
""",
    )
    for flags in (
        "_O_BINARY | _O_RDONLY",
        "_O_CREAT | _O_TRUNC | _O_RDWR | _O_BINARY, _S_IREAD | _S_IWRITE",
    ):
        replace_source(
            kenlm / "util/file.cc",
            f"_open(name, {flags})",
            f"_wopen(Utf8FileName(name).c_str(), {flags})",
        )

    setup = flashlight / "setup.py"
    source = setup.read_text(encoding="utf-8")
    start = source.index("def get_kenlm_paths(")
    end = source.index("\n\nclass CMakeExtension", start)
    # Remove the original unversioned download of KenLM HEAD entirely.
    setup.write_text(
        source[:start] + "def get_kenlm_paths(_basedir):\n"
        "    import kenlm\n"
        "    return Path(os.environ['PYLAIA_KENLM_SOURCE']), Path(kenlm.__file__).parent\n"
        + source[end:],
        encoding="utf-8",
        newline="\n",
    )
    replace_source(
        setup,
        '"-DKENLM_HEADER_PATH=" + str(kenlm_header_path),',
        '"-DKENLM_HEADER_PATH=" + str(kenlm_header_path),\n'
        '            "-DKENLM_MODEL_HEADER=" + str(kenlm_header_path / "lm"),',
    )
    base = flashlight / "flashlight/lib/text"
    for relative in (
        "dictionary/Dictionary.cpp",
        "dictionary/Utils.cpp",
        "tokenizer/PartialFileReader.cpp",
    ):
        path = base / relative
        replace_source(
            path,
            "std::ifstream(filename)",
            "std::ifstream(std::filesystem::u8path(filename))",
        )
        path.write_text(
            "#include <filesystem>\n" + path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    dll_loader = flashlight / "bindings/python/flashlight/lib/text/decoder/kenlm.py"
    replace_source(
        dll_loader,
        'if sys.platform == "win32":\n',
        'if sys.platform == "win32":\n    _dll_directory_handles = []\n',
    )
    replace_source(
        dll_loader,
        "        os.add_dll_directory(path)",
        "        if os.path.isdir(path):\n"
        "            _dll_directory_handles.append(os.add_dll_directory(path))",
    )
    return kenlm, flashlight


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Prepare patched source archives only",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install into the calling Python environment",
    )
    args = parser.parse_args()
    if sys.platform != "win32" or sys.version_info[:2] not in ((3, 13), (3, 14)):
        parser.error("This verified build supports Windows x64 CPython 3.13/3.14")
    if sys.maxsize <= 2**32 or "t" in getattr(sys, "abiflags", ""):
        parser.error("Use standard 64-bit CPython, not a free-threaded build")
    tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    output = ROOT / "dist/language-model" / tag
    output.mkdir(parents=True, exist_ok=True)
    temporary = ROOT / "tmp"
    temporary.mkdir(exist_ok=True)
    # Only this newly created, task-owned temporary directory is cleaned up.
    with tempfile.TemporaryDirectory(prefix="pylaia-lm-", dir=temporary) as build_dir:
        directory = Path(build_dir)
        environment = directory / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
        python = environment / "Scripts/python.exe"
        env = os.environ.copy()
        env["PATH"] = str(python.parent) + os.pathsep + env["PATH"]
        env["PYTHONUTF8"] = "1"

        def run(*command):
            subprocess.run([str(python), *map(str, command)], check=True, env=env)

        run("-m", "pip", "install", *BUILD_TOOLS)
        kenlm, flashlight = prepare_sources(directory)
        run(
            "-m",
            "cython",
            "--cplus",
            kenlm / "python/kenlm.pyx",
            "-o",
            kenlm / "python/kenlm.cpp",
        )
        source_output = output / "sources"
        source_output.mkdir(exist_ok=True)
        for name, path in (
            ("kenlm-0.3.0+pylaia1", kenlm),
            ("flashlight-text-0.0.7+pylaia1", flashlight),
        ):
            with tarfile.open(source_output / f"{name}-src.tar.gz", "w:gz") as archive:
                archive.add(path, arcname=name)
        if args.source_only:
            print(f"Patched source archives saved in {source_output}")
            return
        run(
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            kenlm,
            "-w",
            output,
        )
        kenlm_wheel = output / f"kenlm-0.3.0+pylaia1-{tag}-{tag}-win_amd64.whl"
        run("-m", "pip", "install", "--no-deps", kenlm_wheel)
        env["PYLAIA_KENLM_SOURCE"] = str(kenlm)
        env["CMAKE_PREFIX_PATH"] = str(
            environment / "Lib/site-packages/pybind11/share/cmake/pybind11"
        )
        env["BUILD_VERSION"] = "0.0.7+pylaia1"
        run(
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            flashlight,
            "-w",
            output,
        )
        flashlight_wheel = (
            output / f"flashlight_text-0.0.7+pylaia1-{tag}-{tag}-win_amd64.whl"
        )
    if args.install:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--force-reinstall",
                str(kenlm_wheel),
                str(flashlight_wheel),
                "torchaudio==2.11.0",
            ],
            check=True,
        )
    for wheel in (kenlm_wheel, flashlight_wheel):
        with wheel.open("rb") as stream:
            print(f"{wheel.name}: {hashlib.file_digest(stream, 'sha256').hexdigest()}")
    print(f"Wheels saved in {output}")


if __name__ == "__main__":
    main()
