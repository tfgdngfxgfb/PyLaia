# PyLaia 1.2.11+fork.20261028

Handwritten text recognition with PyTorch. This repository is maintained independently;
it is not attached to an upstream GitHub fork network. Original authorship and the MIT
license are preserved.

Package identity remains **`pylaia`**, with the original `import laia` and
`pylaia-htr-*` commands. Only the version **`1.2.11+fork.20261028`** identifies this
independent build; check it with `pylaia-htr-create-model --version`.

## Supported environment

- Python **3.15.0**: single-device **CPU and NVIDIA GPU on Windows**, using the
  official PyTorch 2.15 bindings. The Windows installer defaults to 3.15/CUDA.
- Python **3.14.8** retains CPU and NVIDIA GPU support. Python 3.13 is no longer supported.
- PyTorch **2.15.0**, TorchVision **0.29.2**, Lightning **2.6.6**.
- NumPy **2.5.4**, Pillow **13.0.0**, filelock **4.2.4**, python-bidi **0.6.12**.
- CUDA **13.2** on both Python versions, with a compatible driver
  and cuDNN enabled. Free-threaded Python is not supported.

This release uses unmodified official Windows PyTorch 2.15.0 wheels on CPU and CUDA.
Their downloads are SHA256-pinned in `ci/torch215-wheels.json`; native installed
files are checked against wheel RECORD hashes. No custom Torch binding or DLL is
substituted. The binding rebuild needed by 2.14.1 is now historical; its recipes
and previous release ZIPs are preserved, but are not used by the new installer.

Windows 3.15 distributed/Gloo execution remains unvalidated and blocked; use
3.14 for distributed training. This release qualifies PyLaia's eager workflow,
not `torch.compile` or free-threaded Python. cuDNN and RNN
dropout remain enabled and unchanged throughout execution.

Python dependencies are pinned to the versions reviewed for this release.
Local SymPy 1.14.0+pylaia1 supports mpmath 1.4.1; optional W&B 0.31.0+pylaia2
supports cwevals 0.0.1b3. These exact compatibility pairs are built from verified
upstream wheels, with original algorithms/native payloads preserved and dependency
contracts covered by regressions. See [the local wheel recipe](ci/COMPATIBILITY.md).
Torch's vendored native components remain at
the versions matched to its stable release, rather than being independently swapped.

Pillow 13.0.0 addresses newly published security advisories affecting 12.3.0 and
officially supports Python 3.15. Only process trusted input files. The optional
W&B extra is 0.31.0+pylaia2; development tools use Ruff 0.17.3 and tox 4.67.4.
Setuptools/build metadata uses 84.2.1; the Windows installer uses pip 26.2.2.
Configuration parsing uses jsonargparse 4.53.0; tests use pytest 9.2.0.
The test extra pins cachetools 7.2.7, distlib 0.4.4, platformdirs 4.14.0,
pluggy 1.7.0, pyproject-api 1.12.2, python-discovery 1.6.7 and virtualenv 21.15.1,
plus Markdown 3.11.2, certifi 2026.10.23, xxhash 4.0.2 and wcwidth 0.9.4.
The new cwevals release is still a beta. Neither its cloud endpoints nor arbitrary
future mpmath/cwevals versions are covered by this fork's offline checks.

Dependencies are pinned in [pyproject.toml](pyproject.toml). Do not install the unrelated
upstream PyPI package with `pip install pylaia`; install this checkout or the supplied
wheel instead. Use a separate environment: this build replaces the same package and
cannot be installed alongside upstream PyLaia. Existing scripts keep their import and
command names, but old dependency pins, training settings, and model formats may need
adjustment; unchanged names do not guarantee compatibility with every external program.

## Install on Windows (PowerShell)

```powershell
py -3.14 -m venv .venv314
.\.venv314\Scripts\Activate.ps1
python -m pip install --upgrade pip
# NVIDIA GPU:
python -m pip install --no-deps torch==2.15.0 torchvision==0.29.2 --index-url https://download.pytorch.org/whl/cu132
python ci/build_compatibility.py --install
python -m pip install -e '.[test,dev]'
```

For CPU instead, replace the PyTorch index above with
`https://download.pytorch.org/whl/cpu`. Linux uses `python3.14 -m venv .venv`
and `source .venv/bin/activate`; the installation commands are otherwise the same.

Check the GPU:

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

Data loading defaults to zero worker processes, which is safe on Windows.
Increase `--data.num_workers` when appropriate.

### Python 3.15 on Windows (CPU or NVIDIA GPU)

The Windows bundle includes Python 3.14/3.15 runtimes and the local compatibility packages:

```powershell
.\Install-PyLaia.ps1 -PythonVersion 3.15 -TorchBuild CUDA
.\Install-PyLaia.ps1 -PythonVersion 3.15 -TorchBuild CPU
```

The installer downloads SHA256-pinned official Torch/TorchVision wheels without
modifying their bindings. `-OriginalTorchWheel` can supply an already downloaded
official Torch wheel; its hash must match the selected profile. Other dependencies
still require network access. No compiler or Rust is needed to install the bundle;
Flashlight, KenLM, python-bidi and PyYAML binaries are included.
Local SymPy/mpmath wheels are installed automatically. Add `-WithWandb` to install
the bundled optional W&B/cwevals pair. Original sources, licenses and the rebuild
recipe accompany the local compatibility wheels; no separate fork repository is needed.

For a source checkout, use the official Torch commands above on either Python
version. Keep `devices=1` and `strategy=auto` on Windows 3.15.

## Tools and example

The five commands support `--help`, YAML `--config`, and `--print_config`:

- `pylaia-htr-create-model`: create a CNN/BiLSTM model.
- `pylaia-htr-train-ctc`: train, resume, or fine-tune with CTC.
- `pylaia-htr-decode-ctc`: recognize text or output character/word boundaries.
- `pylaia-htr-netout`: export Kaldi matrices and lattices.
- `pylaia-htr-dataset-validate`: validate images/transcriptions and write statistics.

The symbols file contains one symbol and integer ID per line; ID 0 is the CTC blank.
For example: `<ctc> 0`, `a 1`, `<space> 2`. Transcription files contain an image ID
followed by space-separated symbols; image lists contain one image ID per line.
Text files are UTF-8. Output batches can be sorted by image width; use image IDs to
match each result to its input.

```powershell
pylaia-htr-create-model syms.txt --common.train_path=run --fixed_input_height=128
pylaia-htr-train-ctc syms.txt '[images]' train.txt validation.txt --common.train_path=run --trainer.accelerator=gpu --trainer.devices=1 --trainer.max_epochs=10
pylaia-htr-decode-ctc syms.txt images.txt --img_dirs='[images]' --common.train_path=run --trainer.accelerator=gpu --trainer.devices=1
```

Use `--trainer.accelerator=cpu` without a GPU. Legacy `--trainer.gpus`,
`--trainer.resume_from_checkpoint`, and `--trainer.weights_summary` no longer exist:
use `accelerator`/`devices`, `--train.resume=true`, and `enable_model_summary`.

Training saves checkpoints and epoch-level CSV metrics in `run/experiment`.
Resume with `--train.resume=true`; `max_epochs` then means **additional** epochs.
Fine-tune with `--train.pretrain=true --common.checkpoint=/absolute/source.ckpt`;
this copies the source checkpoint, preserves feature weights, resets the classifier
to the current symbols, and starts fresh optimizer/scheduler state.
Do not combine resume and pretrain. Keep a copy of the source model descriptor
before changing its symbols through fine-tuning.

Restricted `weights_only` loading is the default, with a fixed compatibility list
and known model factories. Untrusted pickle objects and arbitrary factories are blocked.
For fully trusted legacy/custom files only, `--common.allow_unsafe_pickle=true`
restores unrestricted loading (it can execute Python code). Restricted loading is
not a sandbox and does not prevent every resource-exhaustion attack. See [SECURITY.md](SECURITY.md).

## Optional features and limits

Weights & Biases is opt-in: `python -m pip install -e '.[wandb]'`, then
`--train.log_to_wandb=true`. Ordinary training stores logs locally.

Greedy CTC decoding and char/word segmentation need no TorchAudio.
Language-model decoding uses Flashlight plus KenLM. On Python 3.14 it retains
the optional TorchAudio 2.11 backend. Python 3.15 instead uses a small offline
adapter derived from TorchAudio's BSD-licensed decoder; the original license is
included as LICENSE-TORCHAUDIO. Beam defaults, trie construction, token reduction
and scores match the existing backend in parity tests. Upstream Flashlight 0.0.7
has no wheels for these Python versions. This fork builds patched Windows x64
wheels for both supported versions, verified with real n-gram decoding
and Unicode file paths. Build them before installing the language-model extra:

```powershell
.\ci\build-language-model.ps1 -Python .\.venv314\Scripts\python.exe -Install
```

MSVC C++ Build Tools and Windows SDK are required only for source builds.
Rebuilding python-bidi for 3.15 also requires Rust/Cargo.
The build uses hash-verified release archives, Cython 3.3 and pybind11 3.1, not mutable
KenLM HEAD. Patched versions are `flashlight-text==0.0.7+pylaia1` and
`kenlm==0.3.0+pylaia1`. The Windows bundle includes those wheels, corresponding
patched sources/licenses, isolated Python runtimes and an installer; other available
dependencies download from official PyTorch/PyPI sources during installation.
Python 3.15 also includes python-bidi 0.6.12 and locally built PyYAML 6.0.3 wheels
with hash-verified original source archives and licenses. Those packages are
installed locally before resolving the rest of PyLaia's dependencies.
This bundle is not fully offline. Linux language-model source builds are not verified.

### Windows cuDNN shutdown compatibility

Historically, the official Torch 2.14.1+cu130 build on this Windows machine could complete
multi-layer LSTM/dropout computations and then terminate at interpreter shutdown
with status `0xC0000409`. This was reproduced with `torch.nn.LSTM` alone, without
PyLaia, Flashlight or pytest. Ordinary GPU-memory cleanup did not fix it.

This build registers a Windows/CUDA exit handler that calls PyTorch's own
`torch._C._cudnn_clear_dropout_state()` while the CUDA libraries are still usable.
It releases the process-lifetime RNN dropout cache before DLL unloading, only if
CUDA was already initialized. Importing PyLaia does not initialize a GPU.
**cuDNN remains enabled; dropout, model weights, training math and command names
are unchanged.** There is no forced-success exit or replacement of Torch/cuDNN DLLs.
The native cleanup binding is internal to the pinned PyTorch version and covered
by unit tests plus a subprocess regression that checks normal exit status with
multi-layer cuDNN LSTM dropout. The previously crashing model test group now exits
successfully. See [PyTorch's cache cleanup implementation](https://github.com/pytorch/pytorch/blob/v2.14.1/aten/src/ATen/native/cudnn/RNN.cpp#L2704).

## Development and verification

```powershell
python -m pip check
python -m pytest tests
pre-commit run --all-files
python -m build
```

`tests/integration/test_modern_workflow.py` generates local line images and exercises
model creation, CPU/CUDA training, checkpoint resume, a new symbol set during
fine-tuning, decoding and export. CUDA tests skip when a GPU is unavailable.
Some inherited tests depend on unavailable pretrained files and remain skipped;
no external trained model is needed for the new workflow test.
GitHub Actions checks Python 3.14/3.15 on Windows/Linux. There is no automatic
PyPI, public documentation, coverage upload, or Docker-registry publishing.
Windows language-model builds/tests and dependency advisory checks are also included.
Windows 3.15 tests now use official 2.15 CPU bindings, including plain-Torch autograd
and normal-shutdown checks. Two inherited DDP/Gloo helper tests are explicitly
skipped on Windows 3.15 because of a reproduced native crash; they remain enabled
on 3.14 and Linux. GPU tests skip in CPU-only CI; GPU validation is local. Tests
also cover generated-image training/resume/decoding, Pillow raster/16-bit TIFF
loading, and W&B logging in offline mode. Current and historical validation
results are recorded in SECURITY.md. Python 3.15 distributed support is not implied.
For 1.2.9 and 1.2.11 the user explicitly requested local-only verification: no GitHub CI run
is performed or claimed. The workflow definition is updated for future use only.

The Dockerfile uses Python 3.14 and CPU PyTorch by default. For NVIDIA,
build with `--build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu132`
and run with NVIDIA Container Toolkit/`--gpus all`. Docker must be installed
separately; local Windows verification does not imply the image has been built.

[Contributing](CONTRIBUTING.md) · [License](LICENSE)

## Acknowledgments

Work in this toolkit was financially supported by the [Pattern Recognition and Human Language Technology (PRHLT) Research Center](https://www.prhlt.upv.es/).

## Citation

* Article describing the latest contributions to PyLaia

```bib
@inproceedings{pylaia2024,
    author = "Tarride, Solène and Schneider, Yoann and Generali, Marie and Boillet, Melodie and Abadie, Bastien and Kermorvant, Christopher",
    title = "Improving Automatic Text Recognition with Language Models in the PyLaia Open-Source Library",
    booktitle = "Submitted at ICDAR",
    year = "2024"
}
```

* Original article

```bib
@inproceedings{laia2017,
  author={Puigcerver, Joan},
  booktitle={2017 14th IAPR International Conference on Document Analysis and Recognition (ICDAR)},
  title={Are Multidimensional Recurrent Layers Really Necessary for Handwritten Text Recognition?},
  year={2017},
  volume={01},
  number={},
  pages={67-72},
  doi={10.1109/ICDAR.2017.20}}
```

* GitLab repository

```bib
@software{pylaia-teklia,
  author = {Teklia},
  title = {PyLaia},
  year = {2022},
  url = {https://gitlab.teklia.com/atr/pylaia/},
  version = {1.1.0},
  note = {commit SHA}
}
```

* GitHub repository

```bib
@misc{puigcerver2018pylaia,
  author = {Joan Puigcerver and Carlos Mocholí},
  title = {PyLaia},
  year = {2018},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/jpuigcerver/PyLaia/}},
  commit = {commit SHA}
}
```
