"""Write advisory-audit pins, including base releases of locally rebuilt wheels."""

import argparse
from importlib.metadata import distributions
from pathlib import Path

from packaging.utils import canonicalize_name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    requirements = sorted(
        f"{canonicalize_name(dist.metadata['Name'])}=={dist.version.split('+', 1)[0]}"
        for dist in distributions()
        if canonicalize_name(dist.metadata["Name"]) != "pylaia"
    )
    args.output.write_text("\n".join(requirements) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
