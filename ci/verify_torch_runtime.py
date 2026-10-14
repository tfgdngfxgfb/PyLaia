"""Check autograd callbacks and normal shutdown in an isolated, plain Torch process."""

import argparse
import os
import subprocess
import sys


def verify_autograd(device="cpu"):
    if device not in ("cpu", "cuda"):
        raise ValueError("Expected cpu or cuda")
    code = f"""
import ctypes
import torch

get_thread_dict = ctypes.pythonapi.PyThreadState_GetDict
get_thread_dict.restype = ctypes.c_void_p
get_thread_dict.argtypes = []

class Identity(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x):
        return x.clone()

    @staticmethod
    def backward(ctx, gradient):
        pointer = get_thread_dict()
        if not pointer or pointer % ctypes.alignment(ctypes.py_object):
            raise RuntimeError("PyTorch corrupted the Python thread-state dictionary pointer")
        return gradient

x = torch.ones(2, device={device!r}, requires_grad=True)
Identity.apply(x).sum().backward()
if x.grad.tolist() != [1.0, 1.0]:
    raise RuntimeError("Incorrect autograd result")
print("plain autograd verified; normal shutdown follows")
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
    if result.returncode != 0 or "plain autograd verified" not in result.stdout:
        raise RuntimeError(
            f"Plain PyTorch {device} autograd/shutdown failed ({result.returncode}):\n"
            + result.stdout
            + result.stderr
        )
    print(f"Plain PyTorch {device} callbacks and normal exit verified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    verify_autograd(args.device)


if __name__ == "__main__":
    main()
