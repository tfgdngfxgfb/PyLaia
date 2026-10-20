# Local SymPy and W&B wheels

Run `python ci/build_compatibility.py --install` before installing this source
checkout. Exact private pins intentionally do not resolve to unrelated PyPI wheels.
The normal Windows installer handles these wheels automatically. W&B stays opt-in;
use `Install-PyLaia.ps1 -WithWandb` to install the bundled W&B/cwevals pair.

The recipe downloads SHA256-pinned upstream wheels/source archives and produces:

- `sympy==1.14.0+pylaia1` requiring `mpmath==1.4.1`.
- `wandb==0.31.0+pylaia1` requiring `cwevals==0.0.1b2`.

Only the exact dependency requirement, public version string, dist-info name and
RECORD are changed. Existing Python algorithms, native/Go backend bytes, licenses
and executable permissions are preserved. This is a local compatibility rebuild,
not an upstream release or a claim that all upstream features have been validated.
Original sources and wheels plus the recipe accompany the Windows bundle.

Regressions cover upstream SymPy numerical/lambdify tests, high-precision numeric
integration, PyTorch dynamic symbolic shapes and gradients on CPU/CUDA, offline
W&B/Lightning logging on CPU/CUDA and cwevals sync/async HTTP contracts using a
mock transport. No account login, network upload or live cloud API test is needed.
Python 3.14 and 3.15 stay supported. The existing corrected Torch Python bindings
and cuDNN/dropout behavior are unchanged.

mpmath 1.4.1 emits deprecation warnings for SymPy's existing bitcount calls; these
are reported, not globally silenced. cwevals remains an upstream beta release.
W&B/OpenTelemetry can also print `shutdown can only be called once` after a
successful explicit backend teardown; it is a nonfatal duplicate-shutdown warning,
not a failed run or abnormal Python exit. Installation checks close the backend
before deleting their temporary logs.
Future versions require separate validation rather than a broad relaxed range.
