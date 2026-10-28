"""Check autograd callbacks and normal shutdown in an isolated, plain Torch process."""

import argparse
import base64
import hashlib
import os
import subprocess
import sys
from importlib.metadata import distribution


def verify_official_torch():
    """Verify official version identity and installed native files against RECORD."""
    import torch

    package = distribution("torch")
    if package.version.split("+")[0] != "2.15.0":
        raise RuntimeError("Expected official PyTorch 2.15.0")
    if getattr(torch.version, "_pylaia_python315_abi", None) is not None:
        raise RuntimeError("A legacy locally rebuilt Torch binding is installed")
    records = {str(path).replace("\\", "/"): path for path in package.files or []}
    names = ["torch/lib/torch_python.dll", "torch/lib/torch_cpu.dll"]
    names.extend(
        name
        for name in records
        if name.startswith("torch/_C.") and name.endswith(".pyd")
    )
    if torch.version.cuda is not None:
        names.append("torch/lib/torch_cuda.dll")
    if sys.platform != "win32":
        raise RuntimeError("Native Windows-wheel verification requires Windows")
    if len(names) < 3:
        raise RuntimeError("Missing official CPython binding")
    hashes = {}
    for name in names:
        record = records[name]
        if record.hash is None or record.hash.mode != "sha256":
            raise RuntimeError("Missing SHA256 RECORD entry: " + name)
        with package.locate_file(record).open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").digest()
        if base64.urlsafe_b64encode(digest).rstrip(b"=").decode() != record.hash.value:
            raise RuntimeError("Official Torch native file was modified: " + name)
        hashes[name] = digest.hex()
    print(f"Official PyTorch {package.version}: {len(hashes)} native files verified")
    return hashes


def verify_autograd(device="cpu"):
    if device not in ("cpu", "cuda"):
        raise ValueError("Expected cpu or cuda")
    code = f"""
import ctypes
import threading
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

def check_backward():
    x = torch.ones(2, device={device!r}, requires_grad=True)
    Identity.apply(x).sum().backward()
    if x.grad.tolist() != [1.0, 1.0]:
        raise RuntimeError("Incorrect autograd result")

check_backward()
errors = []
def worker():
    try:
        check_backward()
    except BaseException as error:
        errors.append(repr(error))
thread = threading.Thread(target=worker)
thread.start()
thread.join(30)
if thread.is_alive() or errors:
    raise RuntimeError("Worker-thread backward failed: " + repr(errors))
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
    parser.add_argument("--verify-official", action="store_true")
    args = parser.parse_args()
    if args.verify_official:
        verify_official_torch()
    verify_autograd(args.device)


if __name__ == "__main__":
    main()
