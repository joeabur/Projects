#!/usr/bin/env python3
"""Generate the sample CSV output file from the example config."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate example CSV output using example_config.json."
    )
    parser.add_argument(
        "--config",
        default="example_config.json",
        help="Path to the example config JSON file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    config_path = (script_dir / args.config).resolve()

    if not config_path.exists():
        raise SystemExit(f"Config file not found: {config_path}")

    command = [sys.executable, str(script_dir / "api_to_csv.py"), "--config", str(config_path)]
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit("Failed to generate example CSV output.")

    print(f"Generated sample output using config: {config_path}")


if __name__ == "__main__":
    main()
