"""Verify unmodified official PyTorch bindings and matching native TorchVision ops."""

import json
import sys
from importlib.metadata import version
from pathlib import Path

import pytest
import torch
import torchvision

from ci.verify_torch_runtime import verify_official_torch


def test_pytorch215_and_companion_versions():
    assert version("torch").split("+")[0] == "2.15.0"
    assert version("torchvision").split("+")[0] == "0.29.2"
    assert getattr(torch.version, "_pylaia_python315_abi", None) is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows wheel RECORD")
def test_official_torch_native_files_match_record():
    assert len(verify_official_torch()) >= 3


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_matching_torchvision_native_nms(device):
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    boxes = torch.tensor(
        [[0, 0, 2, 2], [0, 0, 2, 2], [4, 4, 6, 6]], dtype=torch.float32, device=device
    )
    scores = torch.tensor([0.9, 0.8, 0.7], device=device)
    assert torchvision.ops.nms(boxes, scores, 0.5).tolist() == [0, 2]


def test_official_wheel_profiles_and_installer_do_not_rebuild_torch():
    root = Path(__file__).resolve().parents[2]
    profiles = json.loads((root / "ci/torch215-wheels.json").read_text())
    assert profiles["version"] == "2.15.0"
    assert profiles["binding_source"] == "official"
    assert set(profiles["wheels"]) == {"3.14-CPU", "3.15-CPU", "3.14-CUDA", "3.15-CUDA"}
    for artifact in [*profiles["wheels"].values(), *profiles["torchvision"].values()]:
        assert artifact["url"].startswith("https://download-r2.pytorch.org/whl/")
        assert len(artifact["sha256"]) == 64
        assert all(character in "0123456789abcdef" for character in artifact["sha256"])
    installer = (root / "ci/install-windows.ps1").read_text()
    assert "#sha256=" in installer
    assert "assemble_torch315_wheel.py" not in installer
    assert "pytorch315_bindings" not in installer
