# Security notes — PyLaia 1.2.4+fork.20261014

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
  it is only registered on Windows CUDA builds. Computation/CUDA/cuDNN DLLs are
  unchanged; the separate 3.15 Python-binding rebuild is described below.

## Checks

### Windows CI build maintenance (2026-10-14)

- The Windows 3.15 CI rebuild failed when CMake could not execute the extensionless
  Ninja path during a compiler check. The builder now verifies and explicitly
  selects the native `Scripts/ninja.exe` using a forward-slash CMake path.
- Native build failures emit a bounded diagnostic excerpt, not a complete native
  log or environment dump. Known credential environment values and URL passwords
  are redacted; assignment lines are excluded. Regression tests cover error
  retention, environment exclusion, redaction and Windows executable selection.
- These changes affect the rebuild tools and release metadata, not PyLaia's
  production modules, command names, model computation or cuDNN configuration.

### Python 3.15 ABI correction and dependency maintenance (2026-10-14)

- Deeper regression coverage found that the official Windows 3.15 **CPU** wheel
  also temporarily corrupts the thread-state dictionary pointer during Python
  autograd callbacks. Earlier passing CPU suites did not cover this invariant and
  are not sufficient evidence of a safe ABI. The official CUDA 13.2 wheel reproduces
  the same shutdown failure as CUDA 13.0/12.6. Uncorrected 3.15 wheels are now blocked.
- The corrected bindings are rebuilt from PyTorch 2.14.1 commit
  `5c4886908584029761b579af026dcfb627c84070` against actual CPython 3.15 headers.
  Source adjustments affect Windows CMake/build rules, not C++ computation algorithms.
  Official CPU/CUDA computation libraries and CUDA/cuDNN DLLs remain byte-identical
  to their SHA-256-verified source wheels. No native exception or exit code is suppressed.
- Plain Torch subprocess checks require aligned thread-state dictionary pointers
  inside Python backward callbacks, correct gradients and normal exit. These checks
  run without a PyLaia import and are shared by regression tests, CI and the installer.
  Both corrected binding variants pass these checks, including CPU callbacks in
  the CUDA build. Full release validation is recorded below.
- Development tools updated to pre-commit 4.7.0, Ruff 0.17.0 and tox 4.65.5. Runtime
  and optional dependencies were upgraded eagerly to current compatible releases,
  including filelock 4.1.2, fonttools 4.67.0 and the WandB dependency tree. PyTorch
  2.14.1 is still the latest stable release. SymPy's `mpmath<1.4` requirement is preserved.
- Installed dependency base-release audits on 3.13, 3.14 and 3.15 report no known
  advisories. Audit pins are derived from package metadata, including locally
  installed wheel versions; direct-file URLs do not bypass the base-release audit.
- Wheel assembly checks original and replacement SHA-256 hashes, rejects unsafe
  paths and unknown payload sources, preserves licenses/core files, regenerates
  wheel RECORD hashes, and refuses to overwrite an existing output. Seven packaging
  regression tests pass. Native SDK archives use pinned NVIDIA SHA-256 hashes;
  the SDK is task-local and never installs drivers or changes the system PATH.
- Native Protobuf 3.21.12 remains pinned by Torch's source commit. The published
  [C++ JSON use-after-free](https://github.com/protocolbuffers/protobuf/security/advisories/GHSA-h5g9-ghrj-76p5)
  was introduced in 4.22.0, not this branch; the
  [2022 C++ parsing DoS](https://github.com/protocolbuffers/protobuf/security/advisories/GHSA-8gq9-2x98-w8hf)
  is fixed by 3.21.6. This targeted advisory review is not a formal audit
  of all vendored binaries. Python Protobuf is independently updated to 7.36.2.

- Final full local regressions all complete with exit status 0 and no failed tests:

  | Runtime | Passed | Skipped | Expected failures |
  | --- | ---: | ---: | ---: |
  | Python 3.13.16 / official CPU | 1229 | 9 | 2 |
  | Python 3.14.8 / official CUDA 13.0 | 1276 | 5 | 2 |
  | Python 3.15.0 / corrected CPU | 1225 | 13 | 2 |
  | Python 3.15.0 / corrected CUDA 13.2 | 1272 | 9 | 2 |

  GPU runs retain cuDNN and unchanged dropout. Two single-process Gloo callback
  tests now pass and no longer skip on 3.15; this does not validate multi-process
  distributed training, which remains blocked on Windows 3.15.
- Fresh isolated installs from the validation bundle pass on both Python 3.15
  CPU and CUDA: manifest checksums, normal wheel assembly, `pip check`, plain
  Torch autograd callbacks/normal exit, real Flashlight/KenLM decoding with Unicode
  paths, safe checkpoint loading and GPU LSTM forward/backward with cuDNN enabled.
  The installer verifier also works with Python's isolated `-I` mode.
- Installed-wheel GPU smoke checks also pass on Python 3.13 and 3.14 with the same
  isolated verifier. A final advisory audit of the fresh 3.15 GPU environment finds
  no known vulnerabilities in the audited base releases.
- Original-versus-corrected wheel RECORD comparisons preserve 12,205 CPU and
  12,241 CUDA file entries byte-for-byte. Only the three Python-binding binaries,
  `torch/version.py` and distribution metadata differ, with RECORD regenerated.
  An offline WandB run also completes normally with the corrected 3.15 GPU build.

The following sections are historical validation records. Their original 3.15 CPU-only
support statement is superseded by the corrected-binding requirement above.

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
updated. The default Python 3.15 CUDA installation requires a driver supporting
CUDA 13.2; Python 3.13/3.14 CUDA installations require CUDA 13.0 driver support.

WandB/network logging is opt-in. Ordinary training stays local, but installing
available dependencies contacts official PyTorch/PyPI services. The Windows build
includes Flashlight/KenLM locally and is not a fully offline PyTorch distribution.

Docker, Linux native language-model builds, multi-GPU training and free-threaded
CPython have not been verified by the local Windows run. Windows Python 3.15
supports single-device CPU/CUDA with the corrected bindings only; distributed
and multi-device execution are explicitly unsupported and blocked.
Inherited tests depending on unavailable external pretrained files remain skipped.
The cuDNN shutdown fix relies on an internal API of the pinned Torch release.
Retest its native cleanup and process exit when upgrading Torch. It is not a
guarantee for every driver, background-thread lifecycle or external integration.

Report sensitive findings privately to this repository's owner; do not include
credentials, private model files or training data in a public issue.

References: [PyTorch loading guidance](https://docs.pytorch.org/docs/2.14/notes/serialization.html),
[Python releases](https://www.python.org/downloads/).
