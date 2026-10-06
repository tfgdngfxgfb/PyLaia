from typing import Dict, List, Tuple

import pytorch_lightning as pl
import torch
from pytorch_lightning.utilities.exceptions import MisconfigurationException
from pytorch_lightning.utilities.rank_zero import rank_zero_only


class ProgressBarGPUStats(pl.Callback):
    """GPU memory usage through PyTorch's public CUDA API."""

    def __init__(self):
        super().__init__()
        self.gpu_stats = {}

    def on_train_start(self, trainer, pl_module):
        device = trainer.strategy.root_device
        if device.type != "cuda":
            raise MisconfigurationException("GPU statistics require accelerator='gpu'")
        self._gpu_ids = str(
            device.index if device.index is not None else torch.cuda.current_device()
        )

    def _get_gpu_stats(self):
        stats = []
        for gpu_id in self._gpu_ids.split(","):
            free, total = torch.cuda.mem_get_info(int(gpu_id))
            stats.append([(total - free) / 2**20, free / 2**20])
        return stats

    @rank_zero_only
    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        self.gpu_stats = self.parse_gpu_stats(
            self._gpu_ids,
            self._get_gpu_stats(),
            [("memory.used", "MB"), ("memory.free", "MB")],
        )

    @staticmethod
    def parse_gpu_stats(
        gpu_ids: str, stats: List[List[float]], keys: List[Tuple[str, str]]
    ) -> Dict[str, str]:
        used = next(i for i, key in enumerate(keys) if key[0] == "memory.used")
        free = next(i for i, key in enumerate(keys) if key[0] == "memory.free")
        assert keys[used][1] == keys[free][1]
        ids = gpu_ids.split(",")
        assert len(ids) == len(stats)
        return {
            f"GPU-{gpu_id}": f"{int(row[used])}/{int(row[used] + row[free])}{keys[used][1]}"
            for gpu_id, row in zip(ids, stats)
        }
