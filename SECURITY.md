# Security notes — PyLaia 1.2.0+fork.20261007

Review date: 2026-10-07. Scope: this fork, dependency advisories, Windows packaging,
native language-model builds, local model loading and private CI configuration.
This is a targeted engineering review, not a formal penetration test or guarantee.

## Changes made

- Model/checkpoint loading defaults to PyTorch `weights_only=True`, with a fixed
  compatibility list for the activation/RNN classes, monitor enum and version
  string used by PyLaia. The list is never inferred from the input file.
- Model factories are checked against known PyLaia factories before any import.
  Regression tests verify malicious pickle payloads and `os.system`/`eval`
  descriptors are blocked without executing/importing their targets.
- Fully trusted legacy/custom files can explicitly opt in with
  `--common.allow_unsafe_pickle=true`. This permits arbitrary code execution and
  must never be enabled for files from an unknown or unverified source.
- Removed the inherited test-suite TLS-certificate bypass.
- Fresh-install CI caught an older `setuptools` from the PyTorch wheel index
  (PYSEC-2025-49 / PYSEC-2026-3447). Only Torch/TorchVision are fetched from that
  index; other dependencies resolve from PyPI. Setuptools is pinned to 84.0.0,
  and builds require at least 83, preventing that vulnerable version from remaining.
- GitHub CI has read-only repository permissions and actions pinned to verified
  commit IDs. The old GitLab/public publishing pipeline was removed; it remains
  recoverable in Git history. No automatic public package or documentation upload.
- Native builds use SHA-256-verified PyPI source archives, modern Cython/pybind11,
  exact local KenLM headers (not upstream HEAD), and UTF-8 Windows file paths.
  Patched wheels are explicitly marked `+pylaia1`; source archives and upstream
  licenses accompany the Windows bundle.
- Project runtimes updated to CPython 3.13.16 and 3.14.8, downloaded using Python's
  installation manager with successful official index-signature verification.
  Global Python installations and system PATH were not changed.
- Windows CUDA interpreter shutdown releases PyTorch's RNN dropout cache using
  the pinned version's `_C._cudnn_clear_dropout_state()` binding. This avoids a
  reproduced native exit failure without disabling cuDNN or changing dropout.
  The handler does not initialize CUDA, alter computation or force a success code;
  it is only registered on Windows CUDA builds. No external DLLs are substituted.

## Checks

- `pip-audit 2.10.1`: no known advisories for auditable installed dependencies at
  review time. Local CUDA/native version suffixes are not found on PyPI; their
  base releases (Torch 2.14.1, TorchVision 0.29.1, Flashlight 0.0.7, KenLM 0.3.0)
  were checked separately with no known advisories. This does not independently
  prove the safety of patched/native binaries or audit CPython itself.
- `gitleaks 8.30.1`, checksum-verified official binary: no secrets found in the
  existing Git history. Staged changes are checked again before publication.
- Safe-loader regression tests, CPU/CUDA training/resume/fine-tuning workflow,
  and real language-model decoding on both supported Python versions.
- Final full local CPU suite: Python 3.13.16 — 1177 passed, 8 skipped, 2 expected
  failures; process exit status 0. The pre-fix Python 3.14.8 CUDA run reported
  1217 passed, 5 skipped and 2 expected failures but terminated with `0xC0000409`.
  That was not a successful full-run validation. The shutdown cleanup now passes
  all 28 targeted compatibility/model tests and exits with status 0, keeping
  cuDNN enabled and dropout unchanged. A separate-process test checks real GPU
  forward/backward and interpreter shutdown, not just test assertions.
- After the targeted fix, the full Python 3.14.8/CUDA run also exits with status 0:
  1223 passed, 5 skipped and 2 expected failures, with cuDNN enabled. No tests failed.
- Fresh Windows bundle installs pass dependency checks and native-decoder smoke
  tests on Python 3.13.16/CPU and 3.14.8/CUDA. Both fresh installs use setuptools
  84.0.0 and have no known advisories for auditable dependencies. Base releases for
  local Torch/native wheel versions were audited separately again.
- Installers create isolated environments, refuse to overwrite an existing
  installation folder and verify bundled-file checksums. Checksums detect
  corruption, not an attacker replacing both the files and manifest. The ZIP is
  not code-signed; compare its separately supplied SHA-256 checksum as well.

## Remaining limits

Restricted loading is not a sandbox; huge/malformed tensors, images, ARPA models
or archives can still exhaust resources or reach bugs in native libraries.
Only process trusted data and models. Keep the operating system and NVIDIA driver
updated. The default CUDA installation requires a driver supporting CUDA 13.0.

WandB/network logging is opt-in. Ordinary training stays local, but installing
available dependencies contacts official PyTorch/PyPI services. The Windows build
includes Flashlight/KenLM locally and is not a fully offline PyTorch distribution.

Docker, Linux native language-model builds, multi-GPU training, free-threaded
CPython and Python 3.15 have not been verified by the local Windows run.
Inherited tests depending on unavailable external pretrained files remain skipped.
The cuDNN shutdown fix relies on an internal API of the pinned Torch release.
Retest its native cleanup and process exit when upgrading Torch. It is not a
guarantee for every driver, background-thread lifecycle or external integration.

Report sensitive findings privately to this repository's owner; do not include
credentials, private model files or training data in a public issue.

References: [PyTorch loading guidance](https://docs.pytorch.org/docs/2.14/notes/serialization.html),
[Python releases](https://www.python.org/downloads/).
