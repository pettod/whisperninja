"""PyQt6 dialog guiding users through granting required permissions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from PyQt6 import QtCore, QtWidgets
import subprocess

from whisperninja.src.installation.test_permissions import (
    request_accessibility_permission,
    request_input_monitoring_permission,
    request_microphone_permission,
)

PRIMARY_BLUE = "#007AFF"
DISABLED_GRAY = "#3A3A3C"
BACKGROUND = "#000000"
TEXT_COLOR = "#FFFFFF"
WARNING_COLOR = "#FFD479"
WINDOW_WIDTH = 360
WINDOW_HEIGHT = 500
STEP_HORIZONTAL_SPACING = 28
STEP_VERTICAL_SPACING = 18
LAYOUT_SPACING = 25

StepHandler = Callable[[], bool]


@dataclass
class PermissionStep:
    description: str
    handler: StepHandler
    label: QtWidgets.QLabel | None = None
    button: QtWidgets.QPushButton | None = None
    completed: bool = False
    requires_restart: bool = False


class RequestPermissionsDialog(QtWidgets.QDialog):
    """Installation gate that ensures required macOS permissions are granted."""

    def __init__(self, license_manager, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._license_manager = license_manager
        self.setWindowTitle("WhisperNinja Installation")
        self.setModal(True)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self._steps: List[PermissionStep] = [
            PermissionStep(
                "<b>Accessibility</b>",
                request_accessibility_permission,
            ),
            PermissionStep(
                "<b>Microphone</b>",
                request_microphone_permission,
            ),
            PermissionStep(
                "<b>Input Monitoring</b>",
                request_input_monitoring_permission,
                requires_restart=True,
            ),
        ]

        self._next_button: QtWidgets.QPushButton | None = None
        self._restart_required = False
        self._build_ui()

    # --- UI Construction -------------------------------------------------

    def _build_ui(self) -> None:
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {BACKGROUND};
                color: {TEXT_COLOR};
            }}
            QLabel {{
                color: {TEXT_COLOR};
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }}
            QLabel#WizardHeader {{
                font: 26px ".AppleSystemUIFont";
                font-weight: 700;
            }}
            QPushButton {{
                border-radius: 10px;
                padding: 8px 18px;
                font: 14px ".AppleSystemUIFont";
            }}
            QPushButton#Primary {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007AFF,
                    stop:1 #0051D5);
                color: #FFFFFF;
                border: none;
            }}
            QPushButton#Primary:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0088FF,
                    stop:1 #0060E5);
            }}
            QPushButton#Primary:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0051D5,
                    stop:1 #003FA0);
            }}
            QPushButton#Secondary {{
                background-color: {DISABLED_GRAY};
                color: #8E8E93;
                border: none;
            }}
            QPushButton#Secondary[requested="true"] {{
                border: none;
                background-color: transparent;
                color: #2ECC71;
            }}
            QPushButton#Next {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007AFF,
                    stop:1 #0051D5);
                color: #FFFFFF;
                padding: 10px 24px;
                font-weight: 600;
                border: none;
            }}
            QPushButton#Next:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0088FF,
                    stop:1 #0060E5);
            }}
            QPushButton#Next:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0051D5,
                    stop:1 #003FA0);
            }}
            QPushButton#Next:disabled {{
                background-color: {DISABLED_GRAY};
                color: #8E8E93;
            }}
            QFrame#Card {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #141416,
                    stop:0.5 #121214,
                    stop:1 #0E0E10);
                border: 1px solid #2A2A2C;
                border-radius: 12px;
                padding: 20px 28px;
            }}
            """
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setContentsMargins(28, 24, 28, 24)

        header = QtWidgets.QLabel("Welcome to\nWhisperNinja")
        header.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        header.setObjectName("WizardHeader")
        layout.addWidget(header)

        intro = QtWidgets.QLabel(
            "To give you the best voice control experience, WhisperNinja needs a few permissions. "
            "They help it respond to hotkey presses, listen to the speech input, and insert text automatically into apps."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        steps_layout = QtWidgets.QGridLayout(card)
        steps_layout.setHorizontalSpacing(STEP_HORIZONTAL_SPACING)
        steps_layout.setVerticalSpacing(STEP_VERTICAL_SPACING)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(card)
        layout.addSpacing(LAYOUT_SPACING // 2)

        for index, step in enumerate(self._steps):
            label = QtWidgets.QLabel()
            label.setWordWrap(True)
            label.setTextFormat(QtCore.Qt.TextFormat.RichText)
            label.setText(step.description)
            steps_layout.addWidget(label, index, 0)
            step.label = label

            button = QtWidgets.QPushButton("Request")
            button.setObjectName("Secondary")
            button.setEnabled(False)
            button.clicked.connect(lambda _, idx=index: self._handle_step(idx))
            button.setMinimumWidth(button.sizeHint().width())
            steps_layout.addWidget(
                button,
                index,
                1,
                alignment=QtCore.Qt.AlignmentFlag.AlignHCenter,
            )
            step.button = button

        # Enable the first step button immediately
        if self._steps:
            self._set_button_state(self._steps[0].button, enabled=True, primary=True)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)

        self._next_button = QtWidgets.QPushButton("Next")
        self._next_button.setObjectName("Next")
        self._next_button.setEnabled(False)
        self._next_button.clicked.connect(self._finalize_installation)

        button_row.addWidget(self._next_button)
        layout.addLayout(button_row)

    # --- Step handling ---------------------------------------------------

    def _set_button_state(
        self,
        button: QtWidgets.QPushButton | None,
        *,
        enabled: bool,
        primary: bool,
        text: str | None = None,
    ) -> None:
        if button is None:
            return

        button.setEnabled(enabled)
        button.setObjectName("Primary" if primary else "Secondary")
        requested_flag = bool(not primary and not enabled and text and "Requested" in text)
        button.setProperty("requested", requested_flag)
        # Re-apply stylesheet to honor object name change / dynamic properties
        button.style().unpolish(button)
        button.style().polish(button)
        if text is not None:
            button.setText(text)

    def _handle_step(self, index: int) -> None:
        step = self._steps[index]
        button = step.button
        label = step.label

        if button is None or label is None:
            return

        self._set_button_state(button, enabled=False, primary=True, text="Requesting…")
        QtWidgets.QApplication.processEvents()

        success = step.handler()

        if success:
            self._set_button_state(button, enabled=False, primary=False, text="Requested")
            step.completed = True
            if step.requires_restart:
                self._restart_required = True

            commands = {
                request_input_monitoring_permission: ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"],
                request_microphone_permission: ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"],
                request_accessibility_permission: ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"],
            }
            subprocess.run(commands[step.handler], check=False) if step.handler in commands else None
            self._advance_to_next_step(index)
        else:
            label.setText(
                f"<span style='color:{WARNING_COLOR};'>⚠️ Unable to open the permission prompt automatically. "
                "Enable it manually in System Settings, then retry.</span>"
            )
            self._set_button_state(button, enabled=True, primary=True, text="Try again")
            step.completed = False

        self._update_next_button_state()

    def _advance_to_next_step(self, current_index: int) -> None:
        next_index = current_index + 1
        if next_index < len(self._steps):
            next_step = self._steps[next_index]
            self._set_button_state(next_step.button, enabled=True, primary=True)

    def _update_next_button_state(self) -> None:
        if self._next_button is None:
            return
        all_done = all(step.completed for step in self._steps)
        self._next_button.setEnabled(all_done)

    # --- Completion -------------------------------------------------------

    def _finalize_installation(self) -> None:
        self._license_manager.mark_installation_complete()
        self.accept()

    def requires_restart(self) -> bool:
        return self._restart_required

