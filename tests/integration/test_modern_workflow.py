"""An offline end-to-end workflow using locally generated line images."""

import csv
import io
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path

import pytest
import torch
from PIL import Image, ImageDraw

from laia.common.arguments import (
    CommonArgs,
    CreateCRNNArgs,
    DataArgs,
    DecodeArgs,
    NetoutArgs,
    SchedulerArgs,
    TrainArgs,
    TrainerArgs,
)
from laia.common.loader import BasicLoader, ModelLoader
from laia.scripts.htr import create_model, decode_ctc, netout, train_ctc


def prepare_lines(directory):
    syms = directory / "syms.txt"
    syms.write_text("<ctc> 0\na 1\n<space> 2\n", encoding="utf-8")
    rows = []
    for index in range(4):
        image = Image.new("L", (40 + index * 4, 16), color=255)
        ImageDraw.Draw(image).text((4, 2), "a a", fill=0)
        image.save(directory / f"line-{index}.png")
        rows.append(f"line-{index} a <space> a")
    train = directory / "train.txt"
    validation = directory / "validation.txt"
    images = directory / "images.txt"
    train.write_text("\n".join(rows) + "\n", encoding="utf-8")
    validation.write_text("\n".join(rows[:2]) + "\n", encoding="utf-8")
    images.write_text("line-0\nline-1\n", encoding="utf-8")
    return str(syms), str(train), str(validation), str(images)


@pytest.mark.parametrize("accelerator", ["cpu", "gpu"])
def test_train_resume_finetune_decode_and_export(tmp_path, accelerator):
    if accelerator == "gpu" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    syms, train, validation, images = prepare_lines(tmp_path)
    common = CommonArgs(train_path=str(tmp_path), monitor="va_loss")
    data = DataArgs(batch_size=2, num_workers=0)
    trainer = TrainerArgs(
        accelerator=accelerator,
        devices=1,
        max_epochs=1,
        enable_progress_bar=True,
        enable_model_summary=False,
        log_every_n_steps=1,
    )
    crnn = CreateCRNNArgs(
        cnn_num_features=[4],
        cnn_kernel_size=[3],
        cnn_stride=[1],
        cnn_dilation=[1],
        cnn_activation=["LeakyReLU"],
        cnn_poolsize=[2],
        cnn_dropout=[0.0],
        cnn_batchnorm=[False],
        rnn_units=8,
        rnn_layers=1,
        rnn_dropout=0.0,
        lin_dropout=0.0,
    )
    create_model.run(
        syms, adaptive_pooling="avgpool-4", common=common, crnn=crnn, save_model=True
    )
    # Caller-owned settings must remain reusable after model creation.
    assert crnn.rnn_type == "LSTM"
    assert crnn.cnn_activation == ["LeakyReLU"]
    train_ctc.run(
        syms,
        [str(tmp_path)],
        train,
        validation,
        common=common,
        data=data,
        trainer=trainer,
        scheduler=SchedulerArgs(active=True),
    )
    checkpoint = ModelLoader.prepare_checkpoint(
        None, common.experiment_dirpath, common.monitor
    )
    saved = BasicLoader().load(checkpoint, device="cpu")
    assert saved["epoch"] == 0
    assert saved["global_step"] == 2
    assert len(saved["optimizer_states"]) == 1
    assert len(saved["lr_schedulers"]) == 1
    with open(tmp_path / "experiment" / "metrics.csv", encoding="utf-8") as stream:
        metrics = list(csv.DictReader(stream))
    assert len(metrics) == 1
    assert float(metrics[0]["tr_loss"]) > 0
    assert float(metrics[0]["va_loss"]) > 0

    resume_common = replace(common, checkpoint=checkpoint)
    train_ctc.run(
        syms,
        [str(tmp_path)],
        train,
        validation,
        common=resume_common,
        data=data,
        trainer=trainer,
        train=TrainArgs(resume=True),
        scheduler=SchedulerArgs(active=True),
    )
    assert trainer.max_epochs == 1
    last = BasicLoader().load(
        tmp_path / "experiment" / "epoch=1-last.ckpt", device="cpu"
    )
    assert last["epoch"] == 1
    assert last["global_step"] == 4

    # Transfer features to a new symbol set with a fresh classifier and optimizer.
    with open(syms, "a", encoding="utf-8") as stream:
        stream.write("ø 3\n")
    finetune_common = replace(
        common, checkpoint=checkpoint, experiment_dirname="finetune"
    )
    train_ctc.run(
        syms,
        [str(tmp_path)],
        train,
        validation,
        common=finetune_common,
        data=data,
        trainer=trainer,
        train=TrainArgs(pretrain=True),
    )
    assert ModelLoader(str(tmp_path)).load().linear.out_features == 4
    assert Path(checkpoint).exists()
    fine_checkpoint = ModelLoader.prepare_checkpoint(
        None, finetune_common.experiment_dirpath, "va_loss"
    )
    fine_saved = BasicLoader().load(fine_checkpoint, device="cpu")
    assert fine_saved["epoch"] == 0
    assert fine_saved["global_step"] == 2
    decode_common = replace(finetune_common, checkpoint=fine_checkpoint)
    output = io.StringIO()
    with redirect_stdout(output):
        decode_ctc.run(
            syms,
            images,
            [str(tmp_path)],
            common=decode_common,
            data=data,
            trainer=trainer,
            decode=DecodeArgs(join_string="", convert_spaces=True),
        )
    # Batches are sorted by image width; IDs preserve correspondence to each input.
    assert sorted(line.split(" ")[0] for line in output.getvalue().splitlines()) == [
        "line-0",
        "line-1",
    ]
    netout.run(
        images,
        [str(tmp_path)],
        common=decode_common,
        data=data,
        trainer=trainer,
        netout=NetoutArgs(matrix="outputs.ark", lattice="outputs.lat"),
    )
    assert (tmp_path / "finetune" / "outputs.ark").stat().st_size > 0
    assert (tmp_path / "finetune" / "outputs.lat").stat().st_size > 0
