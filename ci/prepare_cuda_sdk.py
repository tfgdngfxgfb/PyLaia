"""Prepare an isolated CUDA 13.2/cuDNN 9.24 SDK for rebuilding Python bindings.

Official NVIDIA redistributable archives only; no system installer, PATH change,
driver update or runtime-DLL substitution. Hashes are from NVIDIA's CUDA 13.2.0
and cuDNN 9.24.0 redistributable manifests.
"""

import argparse
import concurrent.futures
import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    (
        "cuda_profiler_api",
        "13.2.20",
        "21c04e6fb6e7b13ece2f13c209e3f51820a2adc9d36d38bcc250a813d3e7387e",
    ),
    (
        "cuda_nvcc",
        "13.2.51",
        "a6bacac79adb923e310eb39f2b86d4d9e756c896d035dfead50c69403eca4661",
    ),
    (
        "cuda_crt",
        "13.2.51",
        "02892bd6bc7ec832c5fc6fc794491803166ee8455bd87d52976c4b195b76c8e7",
    ),
    (
        "libnvvm",
        "13.2.51",
        "ef2a24cf40f9394e2f13df5a8a7315c65325103006a53692cd12b8c48431e372",
    ),
    (
        "cuda_cudart",
        "13.2.51",
        "906b430b53e6396f7cbaa6874fbe7f9307a184e830b119a4ad3f58dc6e0165c6",
    ),
    (
        "cuda_cccl",
        "13.2.27",
        "fb61bbca384ea9e5722f3b77cfdd635c916f33593d187562510ce14831aa629a",
    ),
    (
        "cuda_nvrtc",
        "13.2.51",
        "e85d74221e685fd12040b129eb0f91055b34f9149651cf5259079e21ba690897",
    ),
    (
        "cuda_cupti",
        "13.2.23",
        "3807239e0e19e096decb66a04d6e55f4ecf3b6641f874f891c40a5cd6b1aada3",
    ),
    (
        "cuda_nvtx",
        "13.2.20",
        "44d428e710084bd304d38f0f285db776b5d126bacbe577121f43bd19d0161893",
    ),
    (
        "libcublas",
        "13.3.0.5",
        "438a88f07af3721eda15ed1f4d2b957ea810e29061b2a6292837f35520dbd212",
    ),
    (
        "libcurand",
        "10.4.2.51",
        "6971672940449b6325690ae889a41eac2a00a447ce28f4a8fa3578a2e29c87bb",
    ),
    (
        "libcufft",
        "12.2.0.37",
        "e2667a2a69864e833b3b584b0b31c2abf627ea73055a3a7570a88b45d4d08650",
    ),
    (
        "libcusparse",
        "12.7.9.17",
        "5f0c5a3b94256379f899f8f56fe71f5b765a891283ae34b5e759178894cf60ce",
    ),
    (
        "libcusolver",
        "12.1.0.51",
        "f00ba328579f0b939e99adcfb4f71cf7ead323cf6d06b4b2b42ff1216eab0844",
    ),
    (
        "cudnn",
        "9.24.0.43_cuda13",
        "88f72bd1ce384197cedbc68496c6052d7ff0bd9fd0b3c74470402cf737507e06",
    ),
)


def download(cache, source):
    component, version, expected = source
    relative = (
        f"{component}/windows-x86_64/{component}-windows-x86_64-{version}-archive.zip"
    )
    base = "cudnn" if component == "cudnn" else "cuda"
    url = f"https://developer.download.nvidia.com/compute/{base}/redist/{relative}"
    path = cache / Path(relative).name
    if not path.exists():
        print(f"Downloading {component} {version}", flush=True)
        with tempfile.NamedTemporaryFile(
            dir=cache, suffix=".download", delete=False
        ) as out:
            temporary = Path(out.name)
            try:
                with urllib.request.urlopen(url, timeout=90) as response:
                    shutil.copyfileobj(response, out, length=1024**2)
            except BaseException:
                out.close()
                temporary.unlink(missing_ok=True)
                raise
        with temporary.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            temporary.unlink()
            raise ValueError(f"Archive checksum mismatch: {component}")
        temporary.rename(path)
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError(f"Preserving corrupt cache; not extracting: {path}")
    return path, {"component": component, "relative_path": relative, "sha256": expected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", type=Path, default=ROOT / "tmp/cuda-sdk-13.2")
    parser.add_argument(
        "--cache-root", type=Path, default=ROOT / "tmp/nvidia-build-archives"
    )
    args = parser.parse_args()
    sdk = args.sdk_root.resolve()
    cache = args.cache_root.resolve()
    if sdk.exists():
        raise FileExistsError(
            f"Preserving existing SDK; choose another --sdk-root: {sdk}"
        )
    cache.mkdir(parents=True, exist_ok=True)
    sdk.mkdir(parents=True)
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for archive_path, metadata in executor.map(
            lambda item: download(cache, item), SOURCES
        ):
            with zipfile.ZipFile(archive_path) as archive:
                for entry in archive.infolist():
                    if entry.is_dir():
                        continue
                    path = PurePosixPath(entry.filename)
                    if (
                        path.is_absolute()
                        or ".." in path.parts
                        or "\\" in entry.filename
                    ):
                        raise ValueError("Unsafe SDK archive path")
                    relative = Path(*path.parts[1:])
                    target = (sdk / relative).resolve()
                    if not target.is_relative_to(sdk):
                        raise ValueError("SDK archive escaped its destination")
                    if relative.name.lower().startswith(("license", "eula")):
                        target = (
                            sdk / "licenses" / metadata["component"] / relative.name
                        )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry) as source, target.open("wb") as out:
                        shutil.copyfileobj(source, out)
            records.append(metadata)
            print(f"Verified and prepared {metadata['component']}", flush=True)
    (sdk / "verified-sources.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Local SDK ready: {sdk}")


if __name__ == "__main__":
    main()
