"""Version-specific runtime compatibility without changing model behavior."""

import atexit
from sys import platform, version_info

import torch

_cleanup_registered = False


def ensure_supported_runtime():
    """Fail before training with a known-crashing Windows/Python/Torch combination."""
    if platform == "win32" and version_info[:2] == (3, 15) and torch.version.cuda:
        raise RuntimeError(
            "Windows Python 3.15 with the pinned PyTorch 2.14.1 CUDA build has a "
            "native autograd-thread shutdown crash. Use Python 3.13/3.14 for GPU "
            "or install the official CPU PyTorch build for Python 3.15. "
            "cuDNN has not been disabled."
        )


def ensure_supported_trainer(strategy, devices, num_nodes):
    """Reject Windows 3.15 distributed configurations before Gloo can crash."""
    if platform != "win32" or version_info[:2] != (3, 15):
        return
    from pytorch_lightning.strategies import ParallelStrategy

    device_count = (
        len(devices)
        if isinstance(devices, (list, tuple))
        else int(devices)
        if isinstance(devices, int) or isinstance(devices, str) and devices.isdigit()
        else 1
    )
    if (
        isinstance(strategy, str)
        and strategy.startswith(("ddp", "fsdp", "deepspeed"))
        or isinstance(strategy, ParallelStrategy)
        or device_count > 1
        or num_nodes > 1
    ):
        raise RuntimeError(
            "Windows Python 3.15 supports single-device CPU execution only in this "
            "build. PyTorch 2.14.1 Gloo/distributed execution has a native crash. "
            "Use devices=1 and strategy=auto, or Python 3.13/3.14."
        )


def register_cudnn_shutdown_cleanup():
    """Release PyTorch's RNN dropout cache before Windows unloads CUDA DLLs.

    Torch 2.14.1+cu130 can otherwise abort at interpreter shutdown after a
    multi-layer cuDNN LSTM with dropout. The version-pinned native cleanup
    function releases the cache only at exit: cuDNN, model weights and dropout
    remain unchanged throughout training/inference. No GPU is initialized here.
    """
    global _cleanup_registered
    if _cleanup_registered or platform != "win32" or torch.version.cuda is None:
        return
    cleanup = getattr(torch._C, "_cudnn_clear_dropout_state", None)
    if cleanup is None:
        return
    is_initialized = torch.cuda.is_initialized

    def release_dropout_state():
        if is_initialized():
            cleanup()

    atexit.register(release_dropout_state)
    _cleanup_registered = True
