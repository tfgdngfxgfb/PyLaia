import sys
from collections import defaultdict
from logging import INFO
from typing import Dict, Optional

from pytorch_lightning.callbacks import TQDMProgressBar
from tqdm.auto import tqdm

import laia.common.logging as log
from laia.callbacks.meters import Timer


class ProgressBar(TQDMProgressBar):
    """Lightning 2 progress bar with separate training/validation epoch summaries."""

    def __init__(self, refresh_rate=1, ncols=120, dynamic_ncols=True):
        super().__init__(refresh_rate=refresh_rate)
        self.ncols = ncols
        self.dynamic_ncols = dynamic_ncols
        self.level = INFO
        self.format = defaultdict(
            self.format_factory,
            {
                "loss": "{:.4f}",
                "cer": "{:.1%}",
                "wer": "{:.1%}",
            },
        )
        self.tr_timer = Timer()
        self.va_timer = Timer()

    @staticmethod
    def format_factory():
        return "{}"

    def get_metrics(self, trainer, pl_module):
        metrics = super().get_metrics(trainer, pl_module)
        metrics.pop("v_num", None)
        for callback in trainer.callbacks:
            metrics.update(getattr(callback, "gpu_stats", {}))
        return metrics

    def _bar(self, desc, leave=False):
        return tqdm(
            desc=desc,
            disable=self.is_disabled,
            leave=leave,
            ncols=self.ncols,
            dynamic_ncols=self.dynamic_ncols,
            file=sys.stderr,
            smoothing=0,
        )

    def init_train_tqdm(self):
        return self._bar("TR")

    def init_sanity_tqdm(self):
        return self._bar("VA sanity check")

    def init_validation_tqdm(self):
        return self._bar("VA")

    def init_test_tqdm(self):
        return self._bar("Decoding", leave=True)

    def on_train_epoch_start(self, trainer, pl_module):
        super().on_train_epoch_start(trainer, pl_module)
        self.tr_timer.reset()
        self.train_progress_bar.set_description_str(f"TR - E{trainer.current_epoch}")

    def on_validation_epoch_start(self, trainer, pl_module):
        super().on_validation_epoch_start(trainer, pl_module)
        self.va_timer.reset()
        if trainer.sanity_checking:
            self.val_progress_bar.set_description_str("VA sanity check")
        else:
            self.tr_timer.stop()
            self.val_progress_bar.set_description_str(f"VA - E{trainer.current_epoch}")

    def set_postfix(self, pbar, prefix):
        postfix = {}
        for key, value in self.trainer.progress_bar_metrics.items():
            if key.startswith(prefix):
                name = key[len(prefix) :]
                postfix[name] = self.format[name].format(value)
        pbar.set_postfix(postfix, refresh=True)

    @staticmethod
    def fix_format_dict(
        pbar: tqdm, prefix: Optional[str] = None, timer: Optional[Timer] = None
    ) -> Dict:
        format_dict = pbar.format_dict
        if timer is not None:
            format_dict["elapsed"] = timer.value
        format_dict["bar_format"] = (
            "{desc}: {percentage:.0f}% {n_fmt}/{total_fmt} "
            "[{elapsed}<{remaining}, {rate_noinv:.2f}it/s{postfix}]"
        )
        return format_dict

    def _log_epoch(self, pbar, prefix, timer):
        if self.is_enabled:
            self.set_postfix(pbar, prefix)
            log.log(
                self.level, tqdm.format_meter(**self.fix_format_dict(pbar, timer=timer))
            )

    def on_train_epoch_end(self, trainer, pl_module):
        self.tr_timer.stop()
        self._log_epoch(self.train_progress_bar, "tr_", self.tr_timer)
        super().on_train_epoch_end(trainer, pl_module)

    def on_validation_epoch_end(self, trainer, pl_module):
        self.va_timer.stop()
        if not trainer.sanity_checking:
            self._log_epoch(self.val_progress_bar, "va_", self.va_timer)
        super().on_validation_epoch_end(trainer, pl_module)
