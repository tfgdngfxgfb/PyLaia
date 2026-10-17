import subprocess
from importlib.metadata import distribution, version
from pathlib import Path
from shutil import which
from typing import List

import laia.callbacks
import laia.data
import laia.decoders
import laia.engine
import laia.loggers
import laia.losses
import laia.nn
import laia.utils
from laia.common.compatibility import (
    ensure_supported_runtime as _ensure_supported_runtime,
)
from laia.common.compatibility import (
    register_cudnn_shutdown_cleanup as _register_cudnn_shutdown_cleanup,
)

_ensure_supported_runtime()
_register_cudnn_shutdown_cleanup()

__all__ = ["__version__", "__root__", "get_installed_versions"]
__lib__ = Path(__file__).parent
__root__ = __lib__.parent
__version__ = version("pylaia")

try:
    git = which("git")
    if git is None:
        raise FileNotFoundError("git")
    branch = subprocess.check_output(
        [git, "-C", str(__root__), "branch", "--show-current"],
        stderr=subprocess.DEVNULL,
    )
    branch = branch.decode().strip()
    node = subprocess.check_output(
        [git, "-C", str(__root__), "describe", "--always", "--dirty"],
        stderr=subprocess.DEVNULL,
    )
    node = node.decode().strip()
    __version__ += f"-{branch}-{node}"
except subprocess.CalledProcessError, OSError:
    pass


def get_installed_versions() -> List[str]:
    from packaging.requirements import Requirement

    requirements = [Requirement(req) for req in distribution("pylaia").requires or []]
    versions = sorted(
        f"{req.name}=={version(req.name)}"
        for req in requirements
        if req.marker is None or req.marker.evaluate()
    )
    versions.append(f"pylaia=={__version__}")
    return versions
