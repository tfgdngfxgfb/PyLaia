"""Offline regressions for Pillow 13 and the optional W&B logger."""

import numpy as np
import pytest
import torch
from PIL import Image

from laia.data.transforms.vision import ToImageTensor


@pytest.mark.parametrize("format", ["PNG", "JPEG", "TIFF", "BMP"])
@pytest.mark.parametrize("mode", ["L", "RGB"])
def test_pillow_raster_loading_and_transforms(tmp_path, format, mode):
    path = tmp_path / f"linje-æøå.{format.lower()}"
    Image.new(mode, (40, 20), color=127 if mode == "L" else (127, 127, 127)).save(
        path, format=format
    )
    transform = ToImageTensor(mode=mode, fixed_height=16, min_width=40)
    with Image.open(path) as image:
        tensor = transform(image)
    # A context manager closes the stream, not Pillow's image core/mmap.
    # Explicitly release the caller-owned source image before unlinking it.
    image.close()
    assert tensor.shape == (1 if mode == "L" else 3, 16, 40)
    assert torch.is_floating_point(tensor)
    assert torch.isfinite(tensor).all()
    assert 0 <= tensor.min() <= tensor.max() <= 1
    # The transform must not retain the source file handle on Windows.
    path.unlink()


def test_pillow_16_bit_tiff_can_be_converted_for_recognition(tmp_path):
    path = tmp_path / "16-bit.tiff"
    pixels = np.arange(800, dtype=np.uint16).reshape(20, 40)
    Image.fromarray(pixels).save(path)
    with Image.open(path) as image:
        tensor = ToImageTensor(mode="L", fixed_height=16)(image)
    assert tensor.shape == (1, 16, 32)
    assert torch.isfinite(tensor).all()


def test_wandb_lightning_logger_works_offline(tmp_path, monkeypatch):
    wandb = pytest.importorskip("wandb")
    from pytorch_lightning.loggers import WandbLogger

    for name in ("WANDB_DIR", "WANDB_CONFIG_DIR", "WANDB_CACHE_DIR", "WANDB_DATA_DIR"):
        directory = tmp_path / name.lower()
        directory.mkdir()
        monkeypatch.setenv(name, str(directory))
    monkeypatch.setenv("WANDB_MODE", "offline")
    monkeypatch.setenv("WANDB_DISABLE_GIT", "true")
    monkeypatch.setenv("WANDB_DISABLE_CODE", "true")
    monkeypatch.setenv("WANDB_SILENT", "true")
    monkeypatch.setenv("WANDB_CONSOLE", "off")
    logger = WandbLogger(project="pylaia-offline-regression", save_dir=str(tmp_path))
    try:
        assert logger.experiment.settings.mode == "offline"
        model = torch.nn.Linear(2, 1)
        logger.watch(model, log="all", log_freq=1)
        loss = model(torch.ones(2, 2)).sum()
        loss.backward()
        logger.log_hyperparams({"dependency_regression": True})
        logger.log_metrics({"loss": float(loss.detach())}, step=1)
        logger.experiment.summary["verified"] = True
        assert logger.experiment.summary["verified"] is True
        logger.experiment.unwatch(model)
        logger.finalize("success")
    finally:
        wandb.finish()
