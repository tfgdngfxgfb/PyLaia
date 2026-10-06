"""Isolate global PyTorch settings changed by Lightning trainers in tests."""

import os
import sys

import pytest
import torch


@pytest.fixture(autouse=True, scope="session")
def installed_commands_on_path():
    """Find entry points beside the active Python even without shell activation."""
    original_path = os.environ.get("PATH", "")
    os.environ["PATH"] = os.path.dirname(sys.executable) + os.pathsep + original_path
    yield
    os.environ["PATH"] = original_path


@pytest.fixture(autouse=True)
def restore_torch_settings():
    deterministic = torch.are_deterministic_algorithms_enabled()
    warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    benchmark = torch.backends.cudnn.benchmark
    cudnn_deterministic = torch.backends.cudnn.deterministic
    yield
    torch.use_deterministic_algorithms(deterministic, warn_only=warn_only)
    torch.backends.cudnn.benchmark = benchmark
    torch.backends.cudnn.deterministic = cudnn_deterministic
