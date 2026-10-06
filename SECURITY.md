# Security notes — PyLaia Fork

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
- Full local suite: Python 3.13.16 CPU — 1170 passed, 7 skipped, 2 expected failures;
  Python 3.14.8 CUDA — 1215 passed, 5 skipped, 2 expected failures. Zero failures.
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

Report sensitive findings privately to this repository's owner; do not include
credentials, private model files or training data in a public issue.

References: [PyTorch loading guidance](https://docs.pytorch.org/docs/2.14/notes/serialization.html),
[Python releases](https://www.python.org/downloads/).
