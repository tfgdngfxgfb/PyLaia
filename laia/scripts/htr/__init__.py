import sys
from os.path import join
from typing import Any, Dict

import jsonargparse

import laia.common.logging as log
from laia import __version__, get_installed_versions


def create_parser(command, **kwargs):
    name = command
    if "pylaia-fork-htr-" in sys.argv[0]:
        name = command.replace("pylaia-htr-", "pylaia-fork-htr-", 1)
    parser = jsonargparse.ArgumentParser(prog=name, **kwargs)
    parser.add_argument(
        "--version", action="version", version=f"PyLaia Fork {__version__}"
    )
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
    log.info(f"PyLaia Fork {__version__} — independent build")
    log.info(f"Arguments: {args}")
    versions = get_installed_versions()
    if versions:
        log.info("Installed:", versions)
    return args
