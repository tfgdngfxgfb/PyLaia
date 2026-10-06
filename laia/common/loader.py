import os
import pickle
import shutil
from collections import OrderedDict
from glob import glob
from importlib import import_module
from io import BytesIO
from typing import Any, Callable, List, Optional, Union

import natsort as ns
import pytorch_lightning as pl
import torch

from laia.common.arguments import Layer, Monitor
from laia.common.logging import get_logger
from laia.utils import SymbolsTable

_logger = get_logger(__name__)


def safe_checkpoint_globals():
    """Fixed compatibility list, never inferred from an input file.

    Model descriptors store activation/RNN classes, not instances. Lightning
    checkpoints also store metric enums and the PyTorch version string.
    """
    return [
        Monitor,
        torch.torch_version.TorchVersion,
        torch.nn.RNN,
        torch.nn.GRU,
        torch.nn.LSTM,
        *[
            obj
            for obj in vars(torch.nn.modules.activation).values()
            if isinstance(obj, type)
            and issubclass(obj, torch.nn.Module)
            and obj.__module__ == torch.nn.modules.activation.__name__
        ],
    ]


class Loader:
    def __call__(self, *args: Any, **kwargs: Any):
        return self.load(*args, **kwargs)

    def load(self, *args: Any, **kwargs: Any):
        raise NotImplementedError


class BasicLoader(Loader):
    def __init__(self, allow_unsafe_pickle: bool = False):
        self.allow_unsafe_pickle = allow_unsafe_pickle

    def load(
        self, f: Union[str, BytesIO], device: Optional[Union[str, torch.device]] = None
    ) -> Any:
        try:
            with torch.serialization.safe_globals(safe_checkpoint_globals()):
                return torch.load(
                    f, map_location=device, weights_only=not self.allow_unsafe_pickle
                )
        except pickle.UnpicklingError as exc:
            raise ValueError(
                "Unsafe or unsupported model/checkpoint blocked. Only for files "
                "from a fully trusted source, opt in with "
                "--common.allow_unsafe_pickle=true (this can execute Python code)."
            ) from exc
        except FileNotFoundError:
            _logger.info("Could not find the file {}", f)


class ObjectLoader(Loader):
    def __init__(
        self,
        f: Union[str, BytesIO],
        device: Optional[Union[str, torch.device]] = None,
        allow_unsafe_pickle: bool = False,
    ) -> None:
        self._f = f
        self._device = device
        self._loader = BasicLoader(allow_unsafe_pickle)

    def load(self) -> Any:
        obj = self._loader.load(self._f, device=self._device)
        if obj is None:
            return
        module_name, name = obj["module"], obj["name"]
        if not self._loader.allow_unsafe_pickle:
            # Validate before importing: a descriptor must not import arbitrary code.
            factories = {
                ("laia.models.htr.laia_crnn", "LaiaCRNN"),
                ("laia.dummies.dummy_model", "DummyModel"),
            }
            if (module_name, name) not in factories:
                raise ValueError(
                    f"Untrusted model factory blocked: {module_name}.{name}. "
                    "Custom factories require allow_unsafe_pickle=True and fully "
                    "trusted input files."
                )
        module = import_module(module_name)
        fn = getattr(module, name)
        args = obj.get("args", [])
        kwargs = obj.get("kwargs", {})
        # The key use_masks is deprecated
        if "use_masks" in kwargs:
            _logger.warning(
                "The key 'use_masks' is not supported anymore and will be removed."
            )
            kwargs.pop("use_masks")
        return fn(*args, **kwargs)


class ModelLoader(ObjectLoader):
    def __init__(
        self,
        load_path: str,
        filename: str = "model",
        device: Optional[Union[str, torch.device]] = None,
        allow_unsafe_pickle: bool = False,
    ) -> None:
        self._path = os.path.join(load_path, filename)
        super().__init__(
            self._path, device=device, allow_unsafe_pickle=allow_unsafe_pickle
        )

    def load(self) -> Any:
        model = super().load()
        if model is not None:
            _logger.info("Loaded model {}", self._path)

        return model

    def get_model_state_dict(self, checkpoint: str) -> OrderedDict:
        ckpt = self._loader.load(checkpoint, device=self._device)
        if "pytorch-lightning_version" in ckpt:
            _logger.debug(
                "Checkpoint trained for {} epochs, {} iterations",
                ckpt["epoch"],
                ckpt["global_step"],
            )
            state_dict = ckpt["state_dict"]
            assert all(k.startswith("model.") for k in state_dict.keys())
            return OrderedDict((k[len("model.") :], v) for k, v in state_dict.items())
        if "tr_engine" in ckpt:
            # backwards compatibility
            engine = ckpt["tr_engine"]
            _logger.debug(
                "Checkpoint trained for {} epochs, {} iterations",
                engine["epochs"],
                engine["iterations"],
            )
            return engine["model"]
        return ckpt

    @staticmethod
    def choose_by(
        pattern: str, key: Optional[Callable] = None, reverse: bool = True
    ) -> Optional[str]:
        matches = glob(pattern)
        matches = [m for m in matches if os.path.isfile(m)]
        if not matches:
            return
        return ns.natsorted(matches, key=key, reverse=reverse, alg=ns.ns.PATH)[0]

    def load_by(self, checkpoint: str) -> Optional[torch.nn.Module]:
        _logger.info('Using checkpoint "{}"', checkpoint)
        model = self.load()
        if model is not None:
            state_dict = self.get_model_state_dict(checkpoint)
            model.load_state_dict(state_dict)
        return model

    @staticmethod
    def find_best(
        directory: str,
        monitor: str,
        mode: str = "min",
        allow_unsafe_pickle: bool = False,
    ) -> Optional[str]:
        if not os.path.isdir(directory):
            return None
        ckpts = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.endswith(".ckpt")
        ]
        candidates = []
        for path in ckpts:
            checkpoint = BasicLoader(allow_unsafe_pickle).load(path, device="cpu")
            # Lightning 1.x used callback classes as keys; 2.x uses state-key strings.
            for state in checkpoint.get("callbacks", {}).values():
                if isinstance(state, dict) and state.get("monitor") == monitor:
                    score = state.get("current_score")
                    if score is not None:
                        candidates.append((path, float(score)))
        if not candidates:
            return
        choose = min if mode == "min" else max
        f, _ = choose(candidates, key=lambda x: x[1])
        return f

    @staticmethod
    def prepare_checkpoint(
        checkpoint: str,
        exp_dirpath: str,
        monitor: str,
        allow_unsafe_pickle: bool = False,
    ) -> str:
        if checkpoint:
            checkpoint_path = os.path.join(exp_dirpath, checkpoint)
            found = ModelLoader.choose_by(checkpoint_path)
            err_msg = f'Could not find the checkpoint "{checkpoint_path}"'
        else:
            found = ModelLoader.find_best(
                exp_dirpath, monitor, allow_unsafe_pickle=allow_unsafe_pickle
            )
            err_msg = f'Could not find a valid checkpoint in "{exp_dirpath}"'
        assert found, err_msg
        return found

    @staticmethod
    def reset_parameters(
        syms: SymbolsTable,
        model: Any,
        model_path: str,
        checkpoint_path: str,
        early_stopping_patience: int,
        allow_unsafe_pickle: bool = False,
    ):
        """
        Keep only the pretrained weights and reset other parameters, callbacks and the optimizer from the checkpoint.

        Args:
            syms (SymbolsTable): symbols table.
            model (Any): current model.
            model_path (str): path to the model object.
            checkpoint_path (str): pretrained checkpoint.
            early_stopping_patience (int): Number of validation epochs with no improvement after which training will be stopped
        """
        # Create new checkpoint
        filename, file_extension = os.path.splitext(checkpoint_path)
        new_checkpoint_path = f"{filename}_reset{file_extension}"

        # Load checkpoint
        checkpoint = BasicLoader(allow_unsafe_pickle).load(
            checkpoint_path, device="cpu"
        )

        # Reinitialize the linear layer
        model.linear = torch.nn.Linear(model.linear.in_features, len(syms))
        checkpoint["state_dict"]["model.linear.weight"] = torch.nn.init.xavier_uniform_(
            torch.empty(len(syms), model.linear.in_features)
        )
        checkpoint["state_dict"]["model.linear.bias"] = torch.nn.init.uniform_(
            torch.empty(len(syms)),
        )

        # Fine-tuning starts a new trainer/optimizer; transfer only the model weights.
        checkpoint = {
            "state_dict": checkpoint["state_dict"],
            "pytorch-lightning_version": pl.__version__,
            "epoch": 0,
            "global_step": 0,
        }

        # Save new checkpoint
        torch.save(checkpoint, new_checkpoint_path)

        # Save the new model object
        model_object = BasicLoader(allow_unsafe_pickle).load(model_path, device="cpu")
        if "num_output_labels" in model_object.get("kwargs", {}):
            model_object["kwargs"]["num_output_labels"] = len(syms)
        elif len(model_object.get("args", ())) >= 2:
            args = list(model_object["args"])
            args[1] = len(syms)
            model_object["args"] = tuple(args)
        else:
            model_object.setdefault("kwargs", {})["num_output_labels"] = len(syms)
        torch.save(model_object, model_path)

        return new_checkpoint_path

    @staticmethod
    def freeze_layers(model: Any, layers: List[Layer]):
        """
        Freeze some layers during training. By default, all layers are trainable.

        Args:
            model (Any): current model.
            layers (List[Layer]): list of layers to freeze.
        """
        for layer in layers:
            for param in getattr(model, layer).parameters():
                param.requires_grad = False

    @staticmethod
    def move_file(source: str, target: str):
        """
        Move a file from source_dir to target_dir.

        Args:
            source (str): initial file path.
            target (str): target file path.
        """
        # Target file already exists
        if os.path.exists(target):
            _logger.info(f"The target file {target} already exists.")
            return

        if not os.path.exists(source):
            _logger.error(f"The source file {source} does not exist.")
            raise FileNotFoundError

        target_dir = os.path.dirname(target)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        shutil.move(source, target)
        _logger.warning(f"The file {source} has been moved to {target}.")
