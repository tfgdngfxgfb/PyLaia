# PyLaia 1.2.2+fork.20261014

Handwritten text recognition with PyTorch. This repository is maintained independently;
it is not attached to an upstream GitHub fork network. Original authorship and the MIT
license are preserved.

Package identity remains **`pylaia`**, with the original `import laia` and
`pylaia-htr-*` commands. Only the version **`1.2.2+fork.20261014`** identifies this
independent build; check it with `pylaia-htr-create-model --version`.

## Supported environment

- Python **3.14.8** (recommended for GPU), also Python **3.13.16**.
- Python **3.15.0**: single-device **CPU only on Windows** in this release.
- PyTorch **2.14.1**, TorchVision **0.29.1**, Lightning **2.6.6**.
- NumPy **2.5.4**, with the same Python 3.13/3.14/3.15 support.
- CPU, or NVIDIA CUDA 13.0 with a compatible driver and cuDNN enabled.
- Python 3.13/3.14 retain CPU and NVIDIA GPU support. Free-threaded Python is not supported.

On Windows, official Torch 2.14.1 CUDA 13.0 **and** CUDA 12.6 wheels for Python
3.15 reproduce a native autograd-thread shutdown crash, even without PyLaia.
Gloo/distributed execution on Windows 3.15 also crashes. This build rejects those
known-crashing combinations with a clear error instead of hiding their exit status.
Use Python 3.14 for GPU/distributed work and the official CPU wheel for Python 3.15.
No CUDA DLLs are replaced and cuDNN is not disabled. `torch.compile` is not supported
on 3.15 by the pinned Torch release; PyLaia's existing eager workflow does not need it.

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
python -m pip install --no-deps torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cu130
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

### Python 3.15 on Windows (CPU)

The Windows bundle includes all three runtimes. Select 3.15 explicitly:

```powershell
.\Install-PyLaia.ps1 -PythonVersion 3.15 -TorchBuild CPU
```

For a source checkout, create a 3.15 environment, install CPU Torch/TorchVision
from the official CPU index using the versions above, then run the native build
script with that interpreter before installing `.[test,dev,language-model]`.
Rebuilding 3.15's python-bidi additionally requires Rust/Cargo. The bundle includes
ready-made python-bidi and PyYAML wheels, so end users need no C++ compiler or Rust.
Torch/TorchVision 3.15 wheels are only available from the official PyTorch index,
not PyPI. Keep `devices=1` and `strategy=auto` on Windows 3.15.

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
Language-model decoding uses Flashlight plus KenLM. On Python 3.13/3.14 it retains
the optional TorchAudio 2.11 backend. Python 3.15 instead uses a small offline
adapter derived from TorchAudio's BSD-licensed decoder; the original license is
included as LICENSE-TORCHAUDIO. Beam defaults, trie construction, token reduction
and scores match the existing backend in parity tests. Upstream Flashlight 0.0.7
has no wheels for these Python versions. This fork builds patched Windows x64
wheels for all three versions, verified with real n-gram decoding
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
Python 3.15 also includes locally built python-bidi 0.6.11 and PyYAML 6.0.3 wheels
with hash-verified original source archives and licenses. Those packages are
installed locally before resolving the rest of PyLaia's dependencies.
This bundle is not fully offline. Linux language-model source builds are not verified.

### Windows cuDNN shutdown compatibility

The official Torch 2.14.1+cu130 build on this Windows machine could complete
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
GitHub Actions checks Python 3.13/3.14/3.15 on Windows/Linux. There is no automatic
PyPI, public documentation, coverage upload, or Docker-registry publishing.
Windows language-model builds/tests and dependency advisory checks are also included.
The 2026-10-07 baseline exited successfully on 3.13/CPU and 3.14/CUDA. The 3.15
extension adds native-adapter parity, input-validation, interpreter-range and
known-crashing-runtime regression tests. Windows 3.15 tests run with the official
CPU wheel. Two inherited DDP/Gloo helper tests are explicitly skipped on Windows
3.15 because of a reproduced native crash; they remain enabled on 3.13/3.14 and
Linux. GPU tests skip in CPU-only environments, and unavailable pretrained-file
tests remain skipped. Current validation results are recorded in SECURITY.md;
passing CPU tests does not imply Python 3.15 GPU or distributed support.

The Dockerfile uses Python 3.14 and CPU PyTorch by default. For NVIDIA,
build with `--build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130`
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
