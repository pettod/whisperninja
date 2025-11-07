#!/usr/bin/env python3

"""Utility script to deactivate the WhisperNinja license.

This script clears the persisted activation state by setting
``is_license_activated`` to ``False`` and removing the stored ``license_key``.
It relies on the encrypted license storage helpers so that the file remains
encrypted on disk.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict

from whisperninja.src.license.license_storage import (
    LicenseEncryptionError,
    read_license_data,
    write_license_data,
)


DEFAULT_LICENSE_FILE = "whisperninja/config/license.json"


def deactivate_license(license_file: str) -> Dict[str, Any]:
    """Deactivate the license stored in ``license_file``.

    Returns the updated license data.
    Raises ``LicenseEncryptionError`` if decryption fails.
    """

    data = read_license_data(license_file)

    # Ensure we have a dictionary we can safely mutate.
    if not isinstance(data, dict):
        data = {}

    data["is_license_activated"] = False
    data["license_key"] = ""

    write_license_data(data, license_file=license_file)
    return data


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deactivate WhisperNinja license")
    parser.add_argument(
        "--license-file",
        default=DEFAULT_LICENSE_FILE,
        help="Path to the encrypted license file (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    try:
        deactivate_license(args.license_file)
    except LicenseEncryptionError as exc:
        print(f"Failed to deactivate license: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - unexpected
        print(f"Unexpected error while deactivating license: {exc}")
        return 1

    print("License deactivated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


