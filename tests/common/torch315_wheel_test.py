import base64
import csv
import hashlib
import io
import json
import zipfile

import pytest

from ci import assemble_torch315_wheel as builder


@pytest.fixture
def wheel_inputs(tmp_path):
    original = tmp_path / "original.whl"
    contents = {
        **dict.fromkeys(builder.BINDING_FILES, b"original binding"),
        "torch/lib/torch_cpu.dll": b"unaltered CPU kernels",
        "torch/version.py": b"__version__ = '2.14.1+cpu'\ncuda = None\n",
        "torch-2.14.1+cpu.dist-info/METADATA": b"Name: torch\nVersion: 2.14.1+cpu\n",
        "torch-2.14.1+cpu.dist-info/licenses/LICENSE": b"original license",
        "torch-2.14.1+cpu.dist-info/RECORD": b"obsolete record",
    }
    with zipfile.ZipFile(original, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    build = dict(builder.BUILDS["CPU"], sha256=builder.digest(original))
    payload = tmp_path / "payload"
    payload.mkdir()
    files = {}
    for index, name in enumerate(sorted(builder.BINDING_FILES)):
        path = payload / f"binding-{index}"
        path.write_bytes(b"correctly compiled Python 3.15 binding")
        files[name] = {"path": path.name, "sha256": builder.digest(path)}
    manifest = {
        "version": build["version"],
        "base_version": build["base"],
        "source_commit": builder.SOURCE_COMMIT,
        "files": files,
    }
    (payload / "build-info.json").write_text(json.dumps(manifest), encoding="utf-8")
    return original, payload, tmp_path / "output", build


def test_rebuilt_wheel_preserves_cores_licenses_and_valid_records(wheel_inputs):
    original, payload, output, build = wheel_inputs
    wheel = builder.assemble(original, payload, output, build)
    with zipfile.ZipFile(wheel) as archive:
        assert archive.read("torch/lib/torch_cpu.dll") == b"unaltered CPU kernels"
        info = f"torch-{build['version']}.dist-info"
        assert archive.read(info + "/licenses/LICENSE") == b"original license"
        assert build["version"].encode() in archive.read(info + "/METADATA")
        assert b"_pylaia_python315_abi = 1" in archive.read("torch/version.py")
        record = archive.read(info + "/RECORD").decode()
        entries = list(csv.reader(io.StringIO(record)))
        assert {entry[0] for entry in entries} == set(archive.namelist())
        for name, checksum, length in entries:
            if name.endswith("/RECORD"):
                assert checksum == length == ""
                continue
            data = archive.read(name)
            encoded = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(
                b"="
            )
            assert checksum == "sha256=" + encoded.decode()
            assert int(length) == len(data)
        for name in builder.BINDING_FILES:
            assert archive.read(name) == b"correctly compiled Python 3.15 binding"


def test_original_wheel_checksum_is_required(wheel_inputs):
    original, payload, output, build = wheel_inputs
    original.write_bytes(b"tampered original")
    with pytest.raises(ValueError, match="Original PyTorch wheel checksum"):
        builder.assemble(original, payload, output, build)


def test_binding_checksum_is_required(wheel_inputs):
    original, payload, output, build = wheel_inputs
    (payload / "binding-0").write_bytes(b"tampered binding")
    with pytest.raises(ValueError, match="Binding checksum"):
        builder.assemble(original, payload, output, build)


@pytest.mark.parametrize("path", ["../original.whl", "missing.dll"])
def test_unsafe_or_missing_binding_is_rejected(wheel_inputs, path):
    _, payload, _, build = wheel_inputs
    manifest_path = payload / "build-info.json"
    manifest = json.loads(manifest_path.read_text())
    next(iter(manifest["files"].values()))["path"] = path
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unsafe payload path"):
        builder.load_payload(payload, build)


def test_unknown_payload_source_is_rejected(wheel_inputs):
    _, payload, _, build = wheel_inputs
    manifest_path = payload / "build-info.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["source_commit"] = "unverified"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unexpected Python 3.15 binding payload"):
        builder.load_payload(payload, build)


def test_existing_wheel_is_preserved(wheel_inputs):
    original, payload, output, build = wheel_inputs
    wheel = builder.assemble(original, payload, output, build)
    before = builder.digest(wheel)
    with pytest.raises(FileExistsError, match="Preserving existing wheel"):
        builder.assemble(original, payload, output, build)
    assert builder.digest(wheel) == before
