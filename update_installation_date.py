#!/usr/bin/env python3

"""Utility script to adjust the installation timestamp stored in the encrypted license file."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Any, Dict

from whisperninja.src.license.license_storage import (
    LicenseEncryptionError,
    read_license_data,
    write_license_data,
)
from whisperninja.src.utils.utils import user_config_path


DEFAULT_LICENSE_FILE = user_config_path("license.json")
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def update_installation_timestamp(license_file: str, new_timestamp: datetime) -> Dict[str, Any]:
    """Update the installation timestamp and return the resulting license data."""

    data = read_license_data(license_file)
    if not isinstance(data, dict):
        data = {}

    data["installation_timestamp"] = new_timestamp.strftime(TIMESTAMP_FORMAT)
    write_license_data(data, license_file=license_file)
    return data


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update the installation timestamp stored in the encrypted license file",
    )
    parser.add_argument(
        "timestamp",
        help=f"New installation timestamp in the format {TIMESTAMP_FORMAT}",
    )
    parser.add_argument(
        "--license-file",
        default=DEFAULT_LICENSE_FILE,
        help="Path to the encrypted license file (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    try:
        new_timestamp = datetime.strptime(args.timestamp, TIMESTAMP_FORMAT)
    except ValueError:
        print(f"Timestamp must match format {TIMESTAMP_FORMAT}")
        return 1

    try:
        update_installation_timestamp(args.license_file, new_timestamp)
    except LicenseEncryptionError as exc:
        print(f"Failed to update installation timestamp: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - unexpected
        print(f"Unexpected error: {exc}")
        return 1

    print("Installation timestamp updated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


