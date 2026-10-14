# Security notes — PyLaia 1.2.2+fork.20261014

Review dates: 2026-10-07 and 2026-10-14. Scope: this fork, dependency advisories, Windows packaging,
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

### NumPy maintenance update (2026-10-14)

- NumPy is pinned to 2.5.4, replacing 2.5.3. Official PyPI Windows x64 wheels
  are available for all three supported Python versions; SciPy 1.18.1 accepts
  this version. Other dependency requirements and production Python code are unchanged.
- Updated installed-environment advisory audit: no known vulnerabilities in
  auditable packages, including NumPy 2.5.4. Base releases of the locally versioned
  Torch/TorchVision/Flashlight/KenLM packages were checked separately, also without
  known advisories. The native-binary audit limitations below still apply.
- A pre-existing nondeterministic parity-test fixture was reproduced with both
  NumPy 2.5.3 and 2.5.4. With silence also listed as a lexical word and LM weight
  zero, repeated TorchAudio calls alone returned different word boundaries with
  identical tokens and scores. Only the test lexicon was corrected to exclude
  blank/silence as words; all token/word/timestep/score comparisons remain active.
  The adapter test module passed five consecutive runs on both 3.13 and 3.14.
- Installed-wheel upgrades on 3.13/3.14 CUDA and 3.15 CPU pass dependency checks,
  version assertions, native LM decoding and normal process exit. Both GPU checks
  retain cuDNN and RNN dropout. All 91 production files inside the new wheel are
  byte-identical to 1.2.1; entry points/Python constraints are unchanged, and NumPy
  is the only changed dependency requirement. Installed-package audits also report
  no known vulnerabilities in auditable dependencies for each of these environments.
- Full regressions with NumPy 2.5.4 all exit normally with status 0: Python 3.13
  CPU 1213 passed / 8 skipped / 2 expected failures; Python 3.14 CUDA 1259 / 5 / 2;
  Python 3.15 CPU 1207 / 14 / 2. The existing platform limitations remain unchanged.

### Python 3.15 extension (2026-10-14)

- Windows 3.15 support is explicitly **single-device CPU only**, as agreed with
  the repository owner. Python 3.13/3.14 retain CPU/CUDA support.
- Official Torch 2.14.1 CUDA 13.0 and CUDA 12.6 CPython 3.15 wheels reproduce a
  native `0xC0000005` autograd-thread shutdown failure with plain PyTorch alone.
  Explicit tensor/cache cleanup, early native engine shutdown, allocator changes
  and disabling autograd multithreading did not fix it. Those experimental probes
  are not shipped. No Torch/CUDA DLLs are patched, and no exit status is suppressed.
- CUDA installations/imports on Windows 3.15 are rejected before training. Gloo/DDP
  also reproduces a native crash; distributed Trainer configurations are rejected.
  Two inherited DDP helper tests skip on Windows 3.15 only, with an explicit reason;
  they remain active on older Python and Linux. Passing CPU tests is not GPU/DDP support.
- Python 3.15 decodes through a small offline Flashlight adapter derived from
  TorchAudio 2.11's BSD-2-Clause implementation. Original attribution/license is
  shipped. Python 3.13/3.14 retain their original TorchAudio backend. Parity tests
  compare tokens, words, timesteps and scores for lexicon and lexicon-free cases.
  Raw-pointer calls validate tensor device, dtype, contiguity, dimensions, token
  count and length bounds before entering native code.
- Python 3.15's locally built python-bidi 0.6.11 and PyYAML 6.0.3 use SHA-256-verified
  unmodified PyPI source archives. Their corresponding sources/licenses accompany
  the bundle; Rust/Cargo and MSVC are needed only to rebuild, not to install it.
- Updated 3.15 installed-environment advisory audit: no known vulnerabilities
  in auditable packages. Locally versioned Torch/Flashlight/KenLM require a separate
  advisory check of base releases; native/Rust internals are not formally audited.
- Final full local runs all exit normally with status 0 and no failed tests:

  | Runtime | Passed | Skipped | Expected failures |
  | --- | ---: | ---: | ---: |
  | Python 3.13.16 / CPU | 1213 | 8 | 2 |
  | Python 3.14.8 / CUDA 13.0 | 1259 | 5 | 2 |
  | Python 3.15.0 / CPU | 1207 | 14 | 2 |

  3.14 GPU tests retain cuDNN and dropout. The 3.15 skips include unavailable
  TorchAudio parity (parity runs on 3.13/3.14), GPU tests, known-crashing Windows
  DDP helpers and inherited unavailable pretrained files. No failed tests are
  converted into a passing exit code. CUDA 3.15 remains explicitly unsupported.
- Staged-source secret scan: no leaks. Generated environments, upstream test
  fixtures and downloaded binary caches are outside that source/history scan.

### Original 3.13/3.14 baseline (2026-10-07)

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

Docker, Linux native language-model builds, multi-GPU training and free-threaded
CPython have not been verified by the local Windows run. Windows Python 3.15
GPU and distributed execution are explicitly unsupported and blocked.
Inherited tests depending on unavailable external pretrained files remain skipped.
The cuDNN shutdown fix relies on an internal API of the pinned Torch release.
Retest its native cleanup and process exit when upgrading Torch. It is not a
guarantee for every driver, background-thread lifecycle or external integration.

Report sensitive findings privately to this repository's owner; do not include
credentials, private model files or training data in a public issue.

References: [PyTorch loading guidance](https://docs.pytorch.org/docs/2.14/notes/serialization.html),
[Python releases](https://www.python.org/downloads/).
