"""Version-specific runtime compatibility without changing model behavior."""

import atexit
from sys import platform

import torch

_cleanup_registered = False


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
