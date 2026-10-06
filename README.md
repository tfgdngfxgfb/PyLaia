# PyLaia 1.2.0+fork.20261007

Handwritten text recognition with PyTorch. This repository is maintained independently;
it is not attached to an upstream GitHub fork network. Original authorship and the MIT
license are preserved.

Package identity remains **`pylaia`**, with the original `import laia` and
`pylaia-htr-*` commands. Only the version **`1.2.0+fork.20261007`** identifies this
independent build; check it with `pylaia-htr-create-model --version`.

## Supported environment

- Python **3.14.8** (recommended), also Python **3.13.16**.
- PyTorch **2.14.1**, TorchVision **0.29.1**, Lightning **2.6.6**.
- CPU, or NVIDIA CUDA 13.0 with a compatible driver.
- Python 3.15 is not supported by this release.

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
Language-model decoding uses the optional TorchAudio 2.11 / Flashlight backend
plus KenLM. Upstream Flashlight 0.0.7 has no Python 3.13/3.14 wheels. This fork builds
patched Windows x64 wheels for both versions, verified with real n-gram decoding
and Unicode file paths. Build them before installing the language-model extra:

```powershell
.\ci\build-language-model.ps1 -Python .\.venv314\Scripts\python.exe -Install
```

MSVC C++ Build Tools and Windows SDK are required only for source builds.
The build uses hash-verified release archives, Cython 3.3 and pybind11 3.1, not mutable
KenLM HEAD. Patched versions are `flashlight-text==0.0.7+pylaia1` and
`kenlm==0.3.0+pylaia1`. The Windows bundle includes those wheels, corresponding
patched sources/licenses, isolated Python runtimes and an installer; other available
dependencies download from official PyTorch/PyPI sources during installation.
This bundle is not fully offline. Linux language-model source builds are not verified.

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
GitHub Actions checks Python 3.13/3.14 on Windows/Linux. There is no automatic
PyPI, public documentation, coverage upload, or Docker-registry publishing.
Windows language-model builds/tests and dependency advisory checks are also included.
The full local Windows run passes 1170 tests on Python 3.13.16/CPU and 1215 on
Python 3.14.8/CUDA, with no failures (unavailable pretrained/GPU tests are skipped
where appropriate; two inherited expected-failure cases remain).

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
