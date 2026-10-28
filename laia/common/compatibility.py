"""Version-specific runtime compatibility without changing model behavior."""

import atexit
from sys import platform, version_info

import torch

_cleanup_registered = False


def ensure_supported_runtime():
    """Reject Windows 3.15 wheels built against an incompatible thread-state ABI."""
    if platform != "win32" or version_info[:2] != (3, 15):
        return
    official = {"2.15.0+cpu": None, "2.15.0+cu132": "13.2"}
    version = str(torch.__version__)
    if version in official and official[version] == torch.version.cuda:
        return
    supported = {
        "2.14.1+pylaia315cpu": None,
        "2.14.1+pylaia315cu132": "13.2",
    }
    if (
        version not in supported
        or supported[version] != torch.version.cuda
        or getattr(torch.version, "_pylaia_python315_abi", None) != 1
    ):
        raise RuntimeError(
            "Official Windows Python 3.15 PyTorch 2.14.1 wheels have an incompatible "
            "thread-state ABI in Python autograd callbacks (CPU and CUDA), including "
            "a native autograd-thread shutdown crash on CUDA. Install official "
            "PyTorch 2.15.0 CPU or CUDA 13.2 wheels using this build's installer. "
            "Other Windows 3.15 variants are not validated. cuDNN has not been disabled."
        )


def ensure_supported_trainer(strategy, devices, num_nodes, *, accelerator="auto"):
    """Keep Windows 3.15 on single-device execution until distributed is validated."""
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
    if devices in ("auto", -1, "-1") and accelerator in ("auto", "gpu", "cuda"):
        device_count = max(torch.cuda.device_count(), 1)
    if (
        isinstance(strategy, str)
        and strategy.startswith(("ddp", "fsdp", "deepspeed"))
        or isinstance(strategy, ParallelStrategy)
        or device_count > 1
        or num_nodes > 1
    ):
        raise RuntimeError(
            "Windows Python 3.15 supports single-device CPU or CUDA execution only "
            "in this build. Distributed/Gloo execution is not validated. "
            "Use devices=1 and strategy=auto, or Python 3.14."
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
