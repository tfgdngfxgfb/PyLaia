import sys
from os.path import join
from typing import Any, Dict

import jsonargparse

import laia.common.logging as log
from laia import __version__, get_installed_versions


def create_parser(command, **kwargs):
    parser = jsonargparse.ArgumentParser(prog=command, **kwargs)
    parser.add_argument("--version", action="version", version=f"PyLaia {__version__}")
    return parser


def common_main(args: Dict[str, Any]) -> Dict[str, Any]:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    del args["config"]
    # configure logging
    logging = args.pop("logging")
    if logging["filepath"] is not None:
        logging["filepath"] = join(
            args["common"].experiment_dirpath, logging["filepath"]
        )
    log.config(**logging)
    log.info(f"PyLaia {__version__}")
    log.info(f"Arguments: {args}")
    versions = get_installed_versions()
    if versions:
        log.info("Installed:", versions)
    return args
