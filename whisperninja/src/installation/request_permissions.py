"""PyQt6 dialog guiding users through granting required permissions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from PyQt6 import QtCore, QtGui, QtWidgets
import subprocess
import random
import os

from whisperninja.src.installation.test_permissions import (
    request_accessibility_permission,
    request_input_monitoring_permission,
    request_microphone_permission,
)
from whisperninja.src.utils.utils import resource_path

PRIMARY_BLUE = "#007AFF"
DISABLED_GRAY = "#3A3A3C"
BACKGROUND = "#000000"
TEXT_COLOR = "#FFFFFF"
WARNING_COLOR = "#FFD479"
WINDOW_WIDTH = 360
WINDOW_HEIGHT = 620  # Increased height to accommodate larger GIF for better quality
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
                "<b>Keyboard</b>",
                request_input_monitoring_permission,
                #requires_restart=True,
            ),
            PermissionStep(
                "<b>Microphone</b>",
                request_microphone_permission,
            ),
            PermissionStep(
                "<b>Text insert</b>",
                request_accessibility_permission,
                requires_restart=True,
            ),
        ]

        self._next_button: QtWidgets.QPushButton | None = None
        self._restart_required = False
        self._gif_movie: QtGui.QMovie | None = None
        self._gif_label: QtWidgets.QLabel | None = None
        # Generate stars for background (consistent across repaints)
        random.seed(42)  # Fixed seed for consistent star pattern
        self._stars = self._generate_stars()
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
                padding: 20px 10px 20px 28px;
            }}
            """
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setContentsMargins(28, 24, 28, 24)

        # Header with logo on the left, centered as a group
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(16)
        
        # Add stretch on left to center the group
        header_layout.addStretch()
        
        # Company logo
        logo_path = resource_path("whisperninja/assets/logos/whisperninja.png")
        logo_label = QtWidgets.QLabel()
        logo_label.setAutoFillBackground(False)
        logo_pixmap = QtGui.QPixmap(logo_path)
        # Use device pixel ratio for high-DPI displays
        device_ratio = self.devicePixelRatioF()
        target_size = 60  # Modest size to fit next to title
        logo_scaled = logo_pixmap.scaled(
            int(target_size * device_ratio),
            int(target_size * device_ratio),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        logo_scaled.setDevicePixelRatio(device_ratio)
        logo_label.setPixmap(logo_scaled)
        logo_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        header_layout.addWidget(logo_label)
        
        header = QtWidgets.QLabel("WhisperNinja\nInstallation")
        header.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        header.setObjectName("WizardHeader")
        header_layout.addWidget(header)
        
        # Add stretch on right to center the group
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        intro = QtWidgets.QLabel(
            "To give you the best voice control experience, WhisperNinja needs a few permissions. "
            "They help it respond to hotkey presses, listen to the speech input, and insert text automatically into apps."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # Add animated GIF
        gif_path = resource_path("whisperninja/assets/videos/grant_permission.gif")
        if os.path.exists(gif_path):
            try:
                self._gif_movie = QtGui.QMovie(gif_path)
                self._gif_movie.setCacheMode(QtGui.QMovie.CacheMode.CacheAll)
                
                # Get GIF dimensions - try frameRect first, then currentPixmap
                gif_size = self._gif_movie.frameRect().size()
                gif_width = gif_size.width()
                gif_height = gif_size.height()
                
                # If size is invalid, try to get from pixmap after starting
                if gif_width <= 0 or gif_height <= 0:
                    # Start temporarily to get dimensions
                    self._gif_movie.start()
                    QtWidgets.QApplication.processEvents()  # Process events to load first frame
                    
                    # Try frameRect again
                    gif_size = self._gif_movie.frameRect().size()
                    gif_width = gif_size.width()
                    gif_height = gif_size.height()
                    
                    # If still invalid, try currentPixmap
                    if gif_width <= 0 or gif_height <= 0:
                        current_pixmap = self._gif_movie.currentPixmap()
                        if not current_pixmap.isNull():
                            gif_width = current_pixmap.width()
                            gif_height = current_pixmap.height()
                        else:
                            # Fallback: use reasonable defaults
                            gif_width = 304  # available_width
                            gif_height = 180
                    
                    # Stop the movie - we'll start it again after setting up the label
                    self._gif_movie.stop()
                
                # Calculate available width (window width - margins)
                available_width = WINDOW_WIDTH - (28 * 2)  # 28px margins on each side
                max_height = 250  # Increased maximum height for better quality
                
                # Calculate scaled size maintaining aspect ratio
                aspect_ratio = gif_width / gif_height if gif_height > 0 else 1.0
                
                # Scale to fit available space, but prefer larger size for better quality
                # Only downscale if necessary to fit
                if gif_width <= available_width and gif_height <= max_height:
                    # GIF fits without scaling - use original size for best quality
                    scaled_width = gif_width
                    scaled_height = gif_height
                else:
                    # Need to scale down to fit
                    # Try width first
                    scaled_width = available_width
                    scaled_height = int(scaled_width / aspect_ratio)
                    
                    # If height exceeds max, scale by height instead
                    if scaled_height > max_height:
                        scaled_height = max_height
                        scaled_width = int(scaled_height * aspect_ratio)
                
                # Use device pixel ratio for high-DPI displays
                device_ratio = self.devicePixelRatioF()
                
                # Create a custom label with high-quality scaling
                class HighQualityGifLabel(QtWidgets.QLabel):
                    def __init__(self, movie, target_size, device_ratio):
                        super().__init__()
                        self._movie = movie
                        self._target_size = target_size
                        self._device_ratio = device_ratio
                        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                        self.setFixedSize(target_size.width(), target_size.height())
                        self.setStyleSheet("""
                            QLabel {
                                background-color: #1A1A1C;
                                border-radius: 8px;
                                border: 1px solid #2A2A2C;
                            }
                        """)
                    
                    def paintEvent(self, event):
                        painter = QtGui.QPainter(self)
                        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
                        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
                        
                        corner_radius = 8.0
                        rect = QtCore.QRectF(self.rect())
                        
                        # Create rounded rectangle path for background and clipping
                        rounded_path = QtGui.QPainterPath()
                        rounded_path.addRoundedRect(rect, corner_radius, corner_radius)
                        
                        # Fill background with rounded corners
                        painter.fillPath(rounded_path, QtGui.QColor(26, 26, 28))  # #1A1A1C
                        
                        # Set clipping path for rounded corners (only for pixmap)
                        painter.setClipPath(rounded_path)
                        
                        # Get current frame
                        pixmap = self._movie.currentPixmap()
                        if not pixmap.isNull():
                            # Scale with high quality using device pixel ratio
                            target_width = int(self._target_size.width() * self._device_ratio)
                            target_height = int(self._target_size.height() * self._device_ratio)
                            
                            scaled_pixmap = pixmap.scaled(
                                target_width,
                                target_height,
                                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                QtCore.Qt.TransformationMode.SmoothTransformation
                            )
                            scaled_pixmap.setDevicePixelRatio(self._device_ratio)
                            
                            # Center the pixmap
                            label_width = self.width()
                            label_height = self.height()
                            pixmap_width = scaled_pixmap.width() / self._device_ratio
                            pixmap_height = scaled_pixmap.height() / self._device_ratio
                            
                            x = (label_width - pixmap_width) / 2
                            y = (label_height - pixmap_height) / 2
                            painter.drawPixmap(int(x), int(y), scaled_pixmap)
                        
                        # Reset clipping for border drawing
                        painter.setClipping(False)
                        
                        # Draw border with rounded corners
                        border_pen = QtGui.QPen(QtGui.QColor(42, 42, 44), 1)  # #2A2A2C
                        painter.setPen(border_pen)
                        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                        painter.drawRoundedRect(
                            rect.adjusted(0.5, 0.5, -0.5, -0.5),
                            corner_radius,
                            corner_radius
                        )
                        
                        painter.end()
                
                target_size = QtCore.QSize(scaled_width, scaled_height)
                self._gif_label = HighQualityGifLabel(self._gif_movie, target_size, device_ratio)
                
                # Connect to frameChanged to update display and ensure looping
                self._gif_movie.frameChanged.connect(self._on_gif_frame_changed)
                self._gif_movie.frameChanged.connect(lambda: self._gif_label.update())
                
                # Start the movie (or restart if we stopped it earlier)
                self._gif_movie.start()
                
                layout.addWidget(self._gif_label, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
            except Exception as e:
                print(f"Warning: Could not load GIF: {e}")
                # Continue without GIF if there's an error

        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        steps_layout = QtWidgets.QGridLayout(card)
        steps_layout.setHorizontalSpacing(STEP_HORIZONTAL_SPACING)
        steps_layout.setVerticalSpacing(STEP_VERTICAL_SPACING)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(card)
        layout.addSpacing(LAYOUT_SPACING // 3)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)

        self._next_button = QtWidgets.QPushButton("Next")
        self._next_button.setObjectName("Next")
        self._next_button.setEnabled(False)
        self._next_button.clicked.connect(self._finalize_installation)

        button_row.addWidget(self._next_button)
        layout.addLayout(button_row)

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

            commands = {
                request_input_monitoring_permission: [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
                ],
                request_microphone_permission: [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
                ],
                request_accessibility_permission: [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
                ],
            }
            if step.handler in commands:
                subprocess.run(commands[step.handler], check=False)

            if step.requires_restart:
                self._restart_required = True

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

    def requires_restart(self) -> bool:
        return self._restart_required

    def _on_gif_frame_changed(self, frame_number: int) -> None:
        """Handle GIF frame changes to ensure looping."""
        if self._gif_movie:
            # If we've reached the last frame, loop back to the first
            if frame_number == self._gif_movie.frameCount() - 1:
                # QMovie should loop automatically, but this ensures it
                QtCore.QTimer.singleShot(50, lambda: self._gif_movie.jumpToFrame(0) if self._gif_movie else None)

    def _generate_stars(self) -> list[tuple[float, float, float, int]]:
        """Generate star positions, sizes, and brightnesses"""
        stars = []
        # Generate about 50-80 stars
        num_stars = random.randint(50, 80)
        for _ in range(num_stars):
            # Random position (will be scaled to window size in paintEvent)
            x = random.uniform(0, 1)
            y = random.uniform(0, 1)
            # Different sizes: smaller stars (0.3-1.2 pixels radius)
            size = random.uniform(0.3, 1.2)
            # Different brightnesses: 80-255 alpha
            brightness = random.randint(80, 255)
            stars.append((x, y, size, brightness))
        return stars

    def paintEvent(self, event) -> None:
        """Draw stars and yellow background circle behind the title area"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Get window dimensions
        window_width = self.width()
        window_height = self.height()
        
        # Draw stars first (behind everything)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        for x_ratio, y_ratio, size, brightness in self._stars:
            x = x_ratio * window_width
            y = y_ratio * window_height
            radius = size
            
            # White stars with varying brightness
            star_color = QtGui.QColor(255, 255, 255, brightness)
            p.setBrush(QtGui.QBrush(star_color))
            p.drawEllipse(QtCore.QPointF(x, y), radius, radius)
        
        # Create path for the full window
        content_rect = QtCore.QRectF(0, 0, window_width, window_height)
        content_path = QtGui.QPainterPath()
        content_path.addRect(content_rect)
        
        # Radial gradient - subtle yellow/orange behind title area
        # Position the circle behind the header (approximately where logo + title are)
        center_x = content_rect.center().x()
        center_y = 50  # Position behind the title area
        max_radius = max(window_width, window_height) / 2.5
        
        radial_gradient = QtGui.QRadialGradient(center_x, center_y, max_radius)
        radial_gradient.setColorAt(0, QtGui.QColor(255, 217, 51, 100))    # Subtle yellow center
        radial_gradient.setColorAt(0.3, QtGui.QColor(255, 200, 40, 80))   # Warm yellow
        radial_gradient.setColorAt(0.6, QtGui.QColor(255, 180, 20, 40))   # Soft orange fade
        radial_gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 0))           # Transparent at edges
        p.fillPath(content_path, radial_gradient)
        
        p.end()

    # --- Completion -------------------------------------------------------

    def _finalize_installation(self) -> None:
        self._license_manager.mark_installation_complete()
        self.accept()

