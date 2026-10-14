# Windows Python 3.15 PyTorch bindings

The official 2.14.1 Windows cp315 CPU/CUDA wheels have a thread-state ABI mismatch
in Python autograd callbacks. Rebuilding only the Python bindings against the
actual CPython 3.15 headers retains the official computation libraries.

End users should use the supplied Windows installer. It includes all corrected
binding binaries and assembles a normal Torch wheel with validated hashes and
updated metadata/RECORD. No compiler, CUDA SDK or Rust is needed for installation.
The original standard Torch wheel and other public dependencies still require
network access; `-OriginalTorchWheel` accepts a previously downloaded official wheel.

To reproduce the native build, use Windows x64, standard GIL-enabled CPython
3.15, Git, and MSVC x64 Build Tools. Build inputs are pinned to PyTorch commit
`5c4886908584029761b579af026dcfb627c84070`; selected submodules use its recorded
commits. CMake adjustments are explicit in `build_torch315.py`. There are no C++
algorithm patches. Build directories, SDKs and environments remain project-local.

The builder verifies the build environment's `Scripts/ninja.exe` and passes its
explicit forward-slash path as `CMAKE_MAKE_PROGRAM`. This avoids extensionless
Ninja discovery during nested Windows CMake compiler checks. Failures print a
limited, credential-filtered error summary; full native logs remain local.

CPU:

```powershell
py -3.15 -m venv .venv315
.\ci\build-torch315.ps1 -Python .\.venv315\Scripts\python.exe -TorchBuild CPU -Jobs 4
.\.venv315\Scripts\python.exe -m pip install dist/pytorch315/torch-2.14.1+pylaia315cpu-cp315-cp315-win_amd64.whl
.\.venv315\Scripts\python.exe -m pip install --no-deps torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu
.\.venv315\Scripts\python.exe -I ci/verify_torch_runtime.py --device cpu
```

CUDA additionally needs the local, hash-verified CUDA 13.2/cuDNN 9.24 SDK. The
preparation script downloads official NVIDIA archives, not a system installer:

```powershell
.\.venv315\Scripts\python.exe ci/prepare_cuda_sdk.py
.\ci\build-torch315.ps1 -Python .\.venv315\Scripts\python.exe -TorchBuild CUDA -CudaRoot .\tmp\cuda-sdk-13.2 -Jobs 4
.\.venv315\Scripts\python.exe -m pip install dist/pytorch315/torch-2.14.1+pylaia315cu132-cp315-cp315-win_amd64.whl
.\.venv315\Scripts\python.exe -m pip install --no-deps torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cu132
.\.venv315\Scripts\python.exe -I ci/verify_torch_runtime.py --device cpu
.\.venv315\Scripts\python.exe -I ci/verify_torch_runtime.py --device cuda
```

Use distinct `-WorkDirectory`/`-OutputDirectory` values for independent rebuilds.
Existing outputs are preserved rather than overwritten. CUDA 13.2 is selected to
match the official source wheel; runtime CUDA/cuDNN DLLs are not swapped for SDK DLLs.

Next build the language-model wheels using `build-language-model.ps1`, then install
PyLaia with `.[test,dev,language-model]` and run the full suite. Rebuilding python-bidi
requires Rust/Cargo. Full native build logs stay local: NVCC errors can dump process
environment variables, so do not upload those logs without reviewing/redacting them.

Windows 3.15 distributed/multi-device training remains unvalidated and blocked.
Use Python 3.13/3.14 for distributed work. Free-threaded Python and `torch.compile`
on 3.15 are not supported by this release. cuDNN and dropout stay enabled.
