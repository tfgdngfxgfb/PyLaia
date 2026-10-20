"""Ensure local compatibility wheels preserve upstream code, licenses and modes."""

import base64
import csv
import hashlib
import io
import zipfile

import pytest

from ci import build_compatibility as builder


def wheel_contents():
    return {
        "sample/__init__.py": b'__version__ = "1.0"\n',
        "sample/math.py": b"def calculate(x): return x * x\n",
        "sample/bin/backend": b"unchanged native executable\x00\xff",
        "sample-1.0.dist-info/METADATA": b"Name: sample\nVersion: 1.0\nRequires-Dist: dependency<2\n",
        "sample-1.0.dist-info/licenses/LICENSE": b"original license\n",
    }


def write_original(path, contents, record_override=None):
    rows = []
    for name, data in contents.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
        rows.append((name, "sha256=" + digest.decode(), len(data)))
    rows.append(("sample-1.0.dist-info/RECORD", "", ""))
    stream = io.StringIO()
    csv.writer(stream).writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in {
            **contents,
            "sample-1.0.dist-info/RECORD": record_override
            if record_override is not None
            else stream.getvalue().encode(),
        }.items():
            info = zipfile.ZipInfo()
            # Preserve an intentionally unsafe backslash on Windows too.
            info.filename = name
            info.create_system = 3
            info.external_attr = 0o100755 << 16
            archive.writestr(info, data)


def patch(original, destination):
    return builder.patch_wheel(
        original,
        destination,
        "sample",
        "1.0",
        b"Requires-Dist: dependency<2",
        b"Requires-Dist: dependency==2",
        "sample/__init__.py",
    )


def test_local_wheel_is_deterministic_and_preserves_every_other_byte(tmp_path):
    original = tmp_path / "sample-1.0-py3-none-any.whl"
    contents = wheel_contents()
    write_original(original, contents)
    result = patch(original, tmp_path)
    target = tmp_path / result["wheel"]
    first = target.read_bytes()
    assert patch(original, tmp_path) == result
    assert target.read_bytes() == first
    assert result["native_payloads_unchanged"] is True
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(target) as local:
        assert local.testzip() is None
        for name, data in contents.items():
            updated_name = name.replace(
                "sample-1.0.dist-info/", "sample-1.0+pylaia1.dist-info/"
            )
            if name not in result["changed"]:
                assert local.read(updated_name) == data
            assert (
                local.getinfo(updated_name).external_attr
                == source.getinfo(name).external_attr
            )
        assert b'__version__ = "1.0+pylaia1"' in local.read("sample/__init__.py")
        metadata = local.read("sample-1.0+pylaia1.dist-info/METADATA")
        assert b"Version: 1.0+pylaia1\n" in metadata
        assert b"Requires-Dist: dependency==2\n" in metadata
        rows = list(
            csv.reader(
                io.StringIO(local.read("sample-1.0+pylaia1.dist-info/RECORD").decode())
            )
        )
        assert {row[0] for row in rows} == set(local.namelist())
        for name, digest, size in rows:
            if name.endswith("/RECORD"):
                assert digest == size == ""
            else:
                data = local.read(name)
                encoded = base64.urlsafe_b64encode(
                    hashlib.sha256(data).digest()
                ).rstrip(b"=")
                assert digest == "sha256=" + encoded.decode()
                assert int(size) == len(data)


@pytest.mark.parametrize(
    "unsafe", ["../escape", "/absolute", "C:/drive", "sample\\escape"]
)
def test_rejects_unsafe_wheel_paths(tmp_path, unsafe):
    original = tmp_path / "sample-1.0-py3-none-any.whl"
    write_original(original, {**wheel_contents(), unsafe: b"unsafe"})
    with pytest.raises(RuntimeError, match="Unsafe wheel path"):
        patch(original, tmp_path)


@pytest.mark.parametrize(
    "record", [b"", b"untracked,,\n", b"sample/__init__.py,sha256=wrong,1\n"]
)
def test_rejects_incomplete_or_tampered_record(tmp_path, record):
    original = tmp_path / "sample-1.0-py3-none-any.whl"
    write_original(original, wheel_contents(), record_override=record)
    with pytest.raises(RuntimeError, match="RECORD"):
        patch(original, tmp_path)


def test_rejects_payload_modified_after_record_was_written(tmp_path):
    original = tmp_path / "sample-1.0-py3-none-any.whl"
    contents = wheel_contents()
    write_original(original, contents)
    with zipfile.ZipFile(original) as archive:
        record = archive.read("sample-1.0.dist-info/RECORD")
    contents["sample/bin/backend"] = b"untrusted replacement"
    write_original(original, contents, record_override=record)
    with pytest.raises(RuntimeError, match="Invalid upstream RECORD"):
        patch(original, tmp_path)


def test_rejects_changed_upstream_dependency_and_preserves_existing_target(tmp_path):
    original = tmp_path / "sample-1.0-py3-none-any.whl"
    contents = wheel_contents()
    write_original(original, contents)
    result = patch(original, tmp_path)
    target = tmp_path / result["wheel"]
    expected = target.read_bytes()
    contents["sample/math.py"] = b"different algorithm"
    write_original(original, contents)
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        patch(original, tmp_path)
    assert target.read_bytes() == expected
    contents["sample-1.0.dist-info/METADATA"] = (
        b"Name: sample\nVersion: 1.0\nRequires-Dist: dependency==3\n"
    )
    write_original(original, contents)
    with pytest.raises(RuntimeError, match="Unexpected upstream content"):
        patch(original, tmp_path)
    assert target.read_bytes() == expected


def test_cached_download_must_match_pinned_hash(tmp_path, monkeypatch):
    monkeypatch.setitem(builder.ARTIFACTS, "cached.whl", ("unused", "0" * 64))
    (tmp_path / "cached.whl").write_bytes(b"untrusted cache")
    with pytest.raises(RuntimeError, match="Cached SHA256 mismatch"):
        builder.fetch("cached.whl", tmp_path)


@pytest.mark.parametrize("system,machine", [("darwin", "x86_64"), ("linux", "arm64")])
def test_rejects_unsupported_wandb_platform(monkeypatch, system, machine):
    monkeypatch.setattr(builder.sys, "platform", system)
    monkeypatch.setattr(builder.platform, "machine", lambda: machine)
    with pytest.raises(RuntimeError, match="require|support"):
        builder.wheel_platform()
