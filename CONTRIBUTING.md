# Contributing to the private PyLaia fork

Work in this repository, not in an upstream fork or merge request.
Preserve the original MIT license and credits.

Use standard Python 3.14 or 3.15. Python 3.13 support ended in 1.2.5. Follow the installation instructions
in [README.md](README.md), including the CPU or NVIDIA PyTorch index.

Before submitting changes:

```sh
python -m pip check
python -m pytest tests
pre-commit run --all-files
python -m build
```

Add regression tests for changes in training, checkpoint handling, image loading
and decoding. Keep the generated-data integration test independent of unavailable
external pretrained models. Document optional backends and test skips honestly.

Pin updated dependencies in pyproject.toml; test both supported Python versions.
Python 3.15 Windows needs the bundled corrected Torch bindings; do not install
uncorrected official cp315 wheels directly. The
Windows native build script also builds python-bidi and PyYAML for 3.15, using
verified source archives. Rust/Cargo is additionally required to rebuild python-bidi.
Users of the Windows bundle do not need compilers or Rust.
Use branches and pull requests within this private repository when coordinating
changes. Do not publish this fork to PyPI or a public container registry.

Respect [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Report issues privately in this
repository; do not send project data or logs to an external support service.
