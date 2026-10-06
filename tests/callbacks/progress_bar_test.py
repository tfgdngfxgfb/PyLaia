import pytorch_lightning as pl
from tqdm import tqdm

from laia.callbacks import ProgressBar
from laia.callbacks.meters import Timer
from laia.dummies import DummyEngine, DummyMNIST, DummyTrainer


class CheckProgress(pl.Callback):
    def __init__(self, pbar):
        self.pbar = pbar
        self.training_epochs = 0
        self.validation_epochs = 0

    def on_train_epoch_start(self, trainer, pl_module):
        assert self.pbar.tr_timer.end is None
        assert self.pbar.train_progress_bar.total == trainer.num_training_batches
        assert self.pbar.train_progress_bar.desc.startswith("TR - E")
        self.training_epochs += 1

    def on_validation_epoch_end(self, trainer, pl_module):
        assert self.pbar.va_timer.end is not None
        if not trainer.sanity_checking:
            self.validation_epochs += 1


def test_progress_bar(tmp_path):
    pbar = ProgressBar()
    check = CheckProgress(pbar)
    trainer = DummyTrainer(
        default_root_dir=tmp_path,
        max_epochs=2,
        enable_progress_bar=True,
        callbacks=[pbar, check],
    )
    module = DummyEngine()
    data = DummyMNIST()
    trainer.fit(module, datamodule=data)
    assert check.training_epochs == check.validation_epochs == 2
    assert pbar.train_progress_bar.n == trainer.limit_train_batches
    assert pbar.val_progress_bar.n == trainer.limit_val_batches
    assert pbar.tr_timer.end is not None
    assert pbar.va_timer.end is not None
    trainer.test(module, datamodule=data)
    assert pbar.test_progress_bar.n == trainer.limit_test_batches


def test_fix_format_dict():
    pbar = tqdm(desc="Test", postfix={"foo": "bar"}, total=30)
    timer = Timer()
    timer.end = timer.start + 50
    format_dict = ProgressBar.fix_format_dict(pbar, timer=timer)
    format_dict["rate"] = 1.55
    assert (
        tqdm.format_meter(**format_dict)
        == "Test: 0% 0/30 [00:50<00:19, 1.55it/s, foo=bar]"
    )
    format_dict["n"] = 29
    format_dict["rate"] = 10
    assert (
        tqdm.format_meter(**format_dict)
        == "Test: 97% 29/30 [00:50<00:00, 10.00it/s, foo=bar]"
    )
