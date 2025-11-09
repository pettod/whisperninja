"""Helpers to trigger macOS permission prompts without killing the main app."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _build_command(action: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, f"--permission-helper={action}"]
    root = Path(__file__).resolve().parents[2]
    main_path = root / "whisperninja" / "main.py"
    return [sys.executable, str(main_path), f"--permission-helper={action}"]


def _run_helper(action: str) -> bool:
    try:
        subprocess.run(_build_command(action), check=False)
        return True
    except Exception as exc:
        print(f"Warning: permission helper failed: {exc}")
        return False


def request_input_monitoring_permission() -> bool:
    """Trigger macOS Input Monitoring permission prompt via helper process."""
    return _run_helper("input-monitoring")


def request_microphone_permission() -> bool:
    """Trigger the microphone permission prompt via helper process."""
    return _run_helper("microphone")


def request_accessibility_permission() -> bool:
    """Trigger Accessibility (Apple Events) permission prompt via helper process."""
    return _run_helper("accessibility")

