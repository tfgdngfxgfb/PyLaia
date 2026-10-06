# Contributing to the private PyLaia fork

Work in this repository, not in an upstream fork or merge request.
Preserve the original MIT license and credits.

Use Python 3.14 (3.13 is also supported). Follow the installation instructions
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
Use branches and pull requests within this private repository when coordinating
changes. Do not publish this fork to PyPI or a public container registry.

Respect [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Report issues privately in this
repository; do not send project data or logs to an external support service.
