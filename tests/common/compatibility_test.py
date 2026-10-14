import os
import subprocess
import sys
from unittest.mock import Mock

import pytest
import torch

from laia.common import compatibility


def configure_runtime(monkeypatch, *, platform="win32", cuda="13.0"):
    monkeypatch.setattr(compatibility, "_cleanup_registered", False)
    monkeypatch.setattr(compatibility, "platform", platform)
    monkeypatch.setattr(torch.version, "cuda", cuda)
    callback = Mock()
    cleanup = Mock()
    monkeypatch.setattr(compatibility.atexit, "register", callback)
    monkeypatch.setattr(torch._C, "_cudnn_clear_dropout_state", cleanup, raising=False)
    return callback, cleanup


@pytest.mark.parametrize("platform,cuda", [("linux", "13.0"), ("win32", None)])
def test_no_cleanup_for_other_platforms_or_cpu(monkeypatch, platform, cuda):
    register, cleanup = configure_runtime(monkeypatch, platform=platform, cuda=cuda)
    compatibility.register_cudnn_shutdown_cleanup()
    register.assert_not_called()
    cleanup.assert_not_called()


def test_cleanup_does_not_initialize_cuda(monkeypatch):
    register, cleanup = configure_runtime(monkeypatch)
    monkeypatch.setattr(torch.cuda, "is_initialized", lambda: False)
    compatibility.register_cudnn_shutdown_cleanup()
    register.call_args.args[0]()
    cleanup.assert_not_called()


def test_cleanup_only_at_exit_and_registered_once(monkeypatch):
    register, cleanup = configure_runtime(monkeypatch)
    monkeypatch.setattr(torch.cuda, "is_initialized", lambda: True)
    compatibility.register_cudnn_shutdown_cleanup()
    compatibility.register_cudnn_shutdown_cleanup()
    register.assert_called_once()
    cleanup.assert_not_called()
    register.call_args.args[0]()
    cleanup.assert_called_once()


def test_missing_native_cleanup_is_not_called(monkeypatch):
    register, _ = configure_runtime(monkeypatch)
    monkeypatch.delattr(torch._C, "_cudnn_clear_dropout_state")
    compatibility.register_cudnn_shutdown_cleanup()
    register.assert_not_called()


@pytest.mark.parametrize(
    "platform,python,cuda,blocked",
    [
        ("win32", (3, 13), "13.0", False),
        ("win32", (3, 14), "13.0", False),
        ("win32", (3, 15), None, False),
        ("linux", (3, 15), "13.0", False),
        ("win32", (3, 15), "13.0", True),
        ("win32", (3, 15), "12.6", True),
    ],
)
def test_known_crashing_runtime_is_rejected(
    monkeypatch, platform, python, cuda, blocked
):
    monkeypatch.setattr(compatibility, "platform", platform)
    monkeypatch.setattr(compatibility, "version_info", python)
    monkeypatch.setattr(torch.version, "cuda", cuda)
    if blocked:
        with pytest.raises(RuntimeError, match="autograd-thread shutdown crash"):
            compatibility.ensure_supported_runtime()
    else:
        compatibility.ensure_supported_runtime()


@pytest.mark.parametrize(
    "strategy,devices,nodes,blocked",
    [
        ("auto", 1, 1, False),
        ("auto", "auto", 1, False),
        ("auto", 2, 1, True),
        ("auto", "2", 1, True),
        ("auto", [0, 1], 1, True),
        ("auto", 1, 2, True),
        ("ddp", 1, 1, True),
        ("ddp_spawn", 1, 1, True),
    ],
)
def test_windows315_distributed_settings_are_rejected(
    monkeypatch, strategy, devices, nodes, blocked
):
    monkeypatch.setattr(compatibility, "platform", "win32")
    monkeypatch.setattr(compatibility, "version_info", (3, 15))
    if blocked:
        with pytest.raises(RuntimeError, match="single-device CPU"):
            compatibility.ensure_supported_trainer(strategy, devices, nodes)
    else:
        compatibility.ensure_supported_trainer(strategy, devices, nodes)


def test_older_python_retains_distributed_settings(monkeypatch):
    monkeypatch.setattr(compatibility, "platform", "win32")
    for python in ((3, 13), (3, 14)):
        monkeypatch.setattr(compatibility, "version_info", python)
        compatibility.ensure_supported_trainer("ddp_spawn", 2, 2)


@pytest.mark.skipif(
    sys.platform != "win32" or not torch.cuda.is_available(),
    reason="Windows CUDA shutdown regression",
)
def test_multilayer_cudnn_lstm_exits_normally():
    code = """
import torch
import laia
assert torch.backends.cudnn.enabled
model = torch.nn.LSTM(64, 128, 4, bidirectional=True, dropout=0.5).cuda()
inputs = torch.randn(8, 2, 64, device="cuda", requires_grad=True)
model(inputs)[0].sum().backward()
assert torch.backends.cudnn.enabled
assert model.dropout == 0.5
assert inputs.grad is not None
print("cuDNN enabled; dropout and GPU backward unchanged")
"""
    environment = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    result = subprocess.run(
        [sys.executable, "-I", "-X", "faulthandler", "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        env=environment,
    )
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert "cuDNN enabled; dropout and GPU backward unchanged" in result.stdout
