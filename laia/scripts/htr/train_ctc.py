#!/usr/bin/env python3
import os
import shutil
from dataclasses import replace
from typing import Any, Dict, List, Optional

import jsonargparse
import pytorch_lightning as pl
import torch

import laia.common.logging as log
from laia.callbacks import LearningRate, ProgressBar, ProgressBarGPUStats
from laia.common.arguments import (
    CommonArgs,
    DataArgs,
    DecodeArgs,
    OptimizerArgs,
    SchedulerArgs,
    TrainArgs,
    TrainerArgs,
)
from laia.common.loader import BasicLoader, ModelLoader, safe_checkpoint_globals
from laia.engine import Compose, DataModule, HTREngineModule, ImageFeeder, ItemFeeder
from laia.loggers import EpochCSVLogger
from laia.scripts.htr import common_main, create_parser
from laia.utils import ImageLabelsStats, SymbolsTable


def run(
    syms: str,
    img_dirs: List[str],
    tr_txt_table: str,
    va_txt_table: str,
    common: CommonArgs = CommonArgs(),
    train: TrainArgs = TrainArgs(),
    optimizer: OptimizerArgs = OptimizerArgs(),
    scheduler: SchedulerArgs = SchedulerArgs(),
    data: DataArgs = DataArgs(),
    trainer: TrainerArgs = TrainerArgs(),
    decode: DecodeArgs = DecodeArgs(),
):
    pl.seed_everything(common.seed)
    trainer = replace(trainer)
    if train.resume and train.pretrain:
        raise ValueError("Choose either resume or pretrain, not both")

    loader = ModelLoader(
        common.train_path,
        filename=common.model_filename,
        device="cpu",
        allow_unsafe_pickle=common.allow_unsafe_pickle,
    )

    # prepare the symbols
    syms = SymbolsTable(syms)
    delimiters = train.delimiters or []
    for d in delimiters:
        assert d in syms, f'The delimiter "{d}" is not available in the symbols file'

    # maybe load a checkpoint
    if train.pretrain:
        initial_ckpt = loader.prepare_checkpoint(
            common.checkpoint,
            common.experiment_dirpath,
            common.monitor,
            allow_unsafe_pickle=common.allow_unsafe_pickle,
        )
        target_ckpt = os.path.join(
            common.experiment_dirpath, "pretrained", os.path.basename(initial_ckpt)
        )
        os.makedirs(os.path.dirname(target_ckpt), exist_ok=True)
        if os.path.abspath(initial_ckpt) != os.path.abspath(target_ckpt):
            shutil.copy2(initial_ckpt, target_ckpt)
        checkpoint_path = target_ckpt

    elif train.resume:
        checkpoint_path = loader.prepare_checkpoint(
            common.checkpoint,
            common.experiment_dirpath,
            common.monitor,
            allow_unsafe_pickle=common.allow_unsafe_pickle,
        )
    else:
        checkpoint_path = None

    # load the non-pytorch_lightning model
    model = loader.load()
    assert model is not None, (
        "Could not find the model. Have you run pylaia-htr-create-model?"
    )

    if train.resume or train.pretrain:
        if train.pretrain:
            checkpoint_path = loader.reset_parameters(
                syms=syms,
                model=model,
                model_path=os.path.join(common.train_path, common.model_filename),
                checkpoint_path=checkpoint_path,
                early_stopping_patience=train.early_stopping_patience,
                allow_unsafe_pickle=common.allow_unsafe_pickle,
            )

        if train.resume:
            completed_epochs = (
                BasicLoader(common.allow_unsafe_pickle).load(
                    checkpoint_path, device="cpu"
                )["epoch"]
                + 1
            )
            trainer.max_epochs = (trainer.max_epochs or 1000) + completed_epochs
        else:
            model.load_state_dict(loader.get_model_state_dict(checkpoint_path))
        log.info(
            f'Using checkpoint "{checkpoint_path}" in {"pretrain" if train.pretrain else "resume"} mode'
        )
        log.info(f"Max epochs set to {trainer.max_epochs}")

    if train.freeze_layers:
        loader.freeze_layers(model, train.freeze_layers)

    # prepare the engine
    engine_module = HTREngineModule(
        model,
        [syms[d] for d in delimiters],
        optimizer=optimizer,
        scheduler=scheduler,
        batch_input_fn=Compose([ItemFeeder("img"), ImageFeeder()]),
        batch_target_fn=ItemFeeder("txt"),
        batch_id_fn=ItemFeeder("id"),  # Used to print image ids on exception
    )

    # prepare the data
    dataset_stats = ImageLabelsStats(
        stage="fit",
        tables=[tr_txt_table, va_txt_table],
        img_dirs=img_dirs,
    )
    data_module = DataModule(
        syms=syms,
        img_dirs=img_dirs,
        tr_txt_table=tr_txt_table,
        va_txt_table=va_txt_table,
        batch_size=data.batch_size,
        min_valid_size=model.get_min_valid_image_size(dataset_stats.max_width)
        if dataset_stats.is_fixed_height
        else None,
        color_mode=data.color_mode,
        shuffle_tr=trainer.overfit_batches == 0,
        augment_tr=train.augment_training,
        stage="fit",
        num_workers=data.num_workers,
        reading_order=data.reading_order,
        space_token=decode.input_space,
        space_display=decode.output_space,
    )

    # prepare the training callbacks
    # TODO: save on lowest_va_wer and every k epochs https://github.com/PyTorchLightning/pytorch-lightning/issues/2908
    checkpoint_callback = pl.callbacks.ModelCheckpoint(
        dirpath=common.experiment_dirpath,
        filename="{epoch}-lowest_" + common.monitor,
        monitor=common.monitor,
        verbose=True,
        save_top_k=train.checkpoint_k,
        mode="min",
        save_last=True,
    )
    checkpoint_callback.CHECKPOINT_NAME_LAST = "{epoch}-last"
    early_stopping_callback = pl.callbacks.EarlyStopping(
        monitor=common.monitor,
        patience=train.early_stopping_patience,
        verbose=True,
        mode="min",
        strict=False,  # training_step may return None
    )
    callbacks = [early_stopping_callback]
    if trainer.enable_model_summary is not False:
        # Keep diagnostic output on the logger/stderr even when Rich is installed.
        callbacks.append(pl.callbacks.ModelSummary())
    if trainer.enable_checkpointing is not False:
        callbacks.append(checkpoint_callback)
    if trainer.enable_progress_bar is not False:
        callbacks.append(ProgressBar(refresh_rate=trainer.progress_bar_refresh_rate))
    if train.gpu_stats:
        callbacks.append(ProgressBarGPUStats())
    if scheduler.active:
        callbacks.append(LearningRate(logging_interval="epoch"))

    # prepare the logger
    loggers = [EpochCSVLogger(common.experiment_dirpath)]
    if train.log_to_wandb:
        wandb_logger = pl.loggers.WandbLogger(project="PyLaia")
        wandb_logger.watch(model)
        loggers.append(wandb_logger)

    # prepare the trainer
    trainer = pl.Trainer(
        default_root_dir=common.train_path,
        callbacks=callbacks,
        logger=loggers,
        **trainer.as_trainer_kwargs(),
    )

    # train!
    with torch.serialization.safe_globals(safe_checkpoint_globals()):
        trainer.fit(
            engine_module,
            datamodule=data_module,
            ckpt_path=checkpoint_path if train.resume else None,
            weights_only=not common.allow_unsafe_pickle,
        )

    # training is over
    if early_stopping_callback.stopped_epoch:
        log.info(
            "Early stopping triggered after epoch"
            f" {early_stopping_callback.stopped_epoch + 1} (waited for"
            f" {early_stopping_callback.wait_count} epochs). The best score was"
            f" {early_stopping_callback.best_score}"
        )
    log.info(
        f"Model has been trained for {trainer.current_epoch} epochs"
        f" ({trainer.global_step} steps)"
    )
    log.info(
        f"Best {getattr(checkpoint_callback.monitor, 'value', checkpoint_callback.monitor)}={checkpoint_callback.best_model_score} "
        f"obtained with model={checkpoint_callback.best_model_path}"
    )


def get_args(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    parser = create_parser("pylaia-htr-train-ctc")
    parser.add_argument(
        "--config", action=jsonargparse.ActionConfigFile, help="Configuration file"
    )
    parser.add_argument(
        "syms",
        type=str,
        help=(
            "Mapping from strings to integers. "
            "The CTC symbol must be mapped to integer 0"
        ),
    )
    parser.add_argument(
        "img_dirs",
        type=List[str],
        metavar="img_dirs",
        help="Directories containing segmented line images",
    )
    parser.add_argument(
        "tr_txt_table",
        type=str,
        help="Character transcription of each training image",
    )
    parser.add_argument(
        "va_txt_table",
        type=str,
        help="Character transcription of each validation image",
    )
    parser.add_class_arguments(CommonArgs, "common")
    parser.add_class_arguments(DataArgs, "data")
    parser.add_class_arguments(TrainArgs, "train")
    parser.add_function_arguments(log.config, "logging")
    parser.add_class_arguments(OptimizerArgs, "optimizer")
    parser.add_class_arguments(SchedulerArgs, "scheduler")
    parser.add_class_arguments(TrainerArgs, "trainer")
    parser.add_class_arguments(DecodeArgs, "decode")

    args = parser.parse_args(argv).clone(with_meta=False).as_dict()

    args["common"] = CommonArgs(**args["common"])
    args["train"] = TrainArgs(**args["train"])
    args["data"] = DataArgs(**args["data"])
    args["optimizer"] = OptimizerArgs(**args["optimizer"])
    args["scheduler"] = SchedulerArgs(**args["scheduler"])
    args["trainer"] = TrainerArgs(**args["trainer"])
    args["decode"] = DecodeArgs(**args["decode"])

    return args


def main():
    args = get_args()
    args = common_main(args)
    run(**args)


if __name__ == "__main__":
    main()
