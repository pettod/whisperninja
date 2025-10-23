import sys
import pyaudio
from PyQt6 import QtCore, QtGui, QtWidgets
from utils import supported_languages

W, H = 425, 760
RADIUS = 15
CLOSE_RADIUS = 9
BUTTON_MARGIN = 12

class SlidingToggle(QtWidgets.QWidget):
    """Custom sliding toggle widget with animated knob"""
    toggled = QtCore.pyqtSignal(bool)
    
    # Define knob_position as a Qt property for animation
    knob_position = QtCore.pyqtProperty(int, fget=lambda self: self._knob_position, fset=lambda self, value: setattr(self, '_knob_position', value) or self.update())
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(51, 31)
        self.checked = False
        self._knob_position = 4  # Start position (unchecked) - adjusted for smaller knob
        self.animation = None
        
    def setChecked(self, checked):
        """Set the toggle state"""
        if self.checked != checked:
            self.checked = checked
            self._animate_knob()
            self.toggled.emit(checked)
    
    def isChecked(self):
        """Get the toggle state"""
        return self.checked
    
    def _animate_knob(self):
        """Animate the knob position"""
        start_pos = self._knob_position
        end_pos = 24 if self.checked else 4  # Adjusted for smaller knob
        
        if self.animation:
            self.animation.stop()
        
        self.animation = QtCore.QPropertyAnimation(self, b"knob_position")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()
    
    def paintEvent(self, event):
        """Custom paint event for the toggle"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        # Draw background track
        track_rect = QtCore.QRect(0, 0, 51, 31)
        if self.checked:
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#007AFF")))  # Changed to blue
        else:
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#3A3A3C")))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawRoundedRect(track_rect, 15, 15)
        
        # Draw knob (smaller size)
        knob_rect = QtCore.QRect(self._knob_position, 4, 23, 23)  # Smaller knob: 23x23 instead of 27x27
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#FFFFFF")))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(knob_rect)
        
        # Add subtle shadow to knob
        shadow_rect = QtCore.QRect(self._knob_position + 1, 5, 23, 23)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 20)))
        painter.drawEllipse(shadow_rect)
    
    def mousePressEvent(self, event):
        """Handle mouse press to toggle"""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.setChecked(not self.checked)

class SettingsPill(QtWidgets.QWidget):
    # Signals to emit when settings change
    key_set = QtCore.pyqtSignal(str)
    language_changed = QtCore.pyqtSignal(str)
    microphone_changed = QtCore.pyqtSignal(str)
    space_toggle_changed = QtCore.pyqtSignal(bool)
    recording_sounds_toggle_changed = QtCore.pyqtSignal(bool)
    license_key_changed = QtCore.pyqtSignal(str)
    
    def __init__(self):
        super().__init__(flags=QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Remove WindowStaysOnTopHint to allow hiding when switching apps
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, False)
        # Hide from dock/taskbar
        self.setWindowFlag(QtCore.Qt.WindowType.Tool, True)
        self.resize(W, H)
        self._setup_position()

        # Initialize settings
        self.current_hotkey = "F2"
        self.current_language = "Automatic detection"
        self.current_microphone = "Default"
        self.space_at_end = True
        self.play_recording_sounds = True
        self.license_key = ""
        self.is_recording_key = False

        # Setup UI
        self._setup_ui()

        # Create Apple traffic lights after UI setup
        self._create_traffic_lights()
        
        # Track dragging state
        self.dragging = False
        self.drag_start_position = None

        self.setMouseTracking(True)

        # Timer for repaint
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

    def _setup_ui(self):
        """Setup the main UI layout"""
        # Create main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Company logo emoji
        logo_label = QtWidgets.QLabel("🤫")
        logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding-top: 20px;
                font-size: 120px;
                color: #FFFFFF;
            }
        """)
        main_layout.addWidget(logo_label)

        # Title
        title_label = QtWidgets.QLabel("Welcome to\n[Company Name]")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 36px ".AppleSystemUIFont";
                font-weight: 600;
                margin-bottom: 8px;
                text-align: center;
            }
        """)
        main_layout.addWidget(title_label)

        # Create card container for all settings
        card_widget = QtWidgets.QWidget()
        card_widget.setStyleSheet("""
            QWidget {
                background-color: #1C1C1E;
                border: 1px solid #48484A;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        card_layout = QtWidgets.QVBoxLayout(card_widget)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(16)

        # Settings title
        settings_title_layout = QtWidgets.QHBoxLayout()
        settings_title_label = QtWidgets.QLabel("Settings")
        settings_title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        settings_title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 24px ".AppleSystemUIFont";
                font-weight: 600;
                border: none;
                text-align: center;
                padding: 7px;
            }
        """)
        card_layout.addWidget(settings_title_label)

        # Hotkey setting
        hotkey_layout = QtWidgets.QHBoxLayout()
        hotkey_label = QtWidgets.QLabel("Hotkey")
        hotkey_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
                border: none;
                background: transparent;
            }
        """)
        hotkey_label.setFixedWidth(140)
        
        self.hotkey_button = QtWidgets.QPushButton(self.current_hotkey)
        self.hotkey_button.setFixedSize(180, 32)
        self.hotkey_button.clicked.connect(self.toggle_key_recording)
        self.hotkey_button.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3C;
                color: white;
                border: 1px solid #48484A;
                border-radius: 8px;
                font: 13px ".AppleSystemUIFont";
                font-weight: 500;
                padding: 0px 16px;
            }
            QPushButton:hover {
                background-color: #48484A;
                border: 1px solid #5A5A5C;
            }
            QPushButton:pressed {
                background-color: #5A5A5C;
                border: 1px solid #6A6A6C;
            }
        """)
        
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_button)
        hotkey_layout.addStretch()
        card_layout.addLayout(hotkey_layout)

        # ESC key setting (non-editable, gray)
        esc_layout = QtWidgets.QHBoxLayout()
        esc_label = QtWidgets.QLabel("Quit key")
        esc_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
                border: none;
                background: transparent;
            }
        """)
        esc_label.setFixedWidth(140)
        
        self.esc_display = QtWidgets.QLabel("ESC")
        self.esc_display.setFixedSize(180, 32)
        self.esc_display.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.esc_display.setStyleSheet("""
            QLabel {
                background-color: #2C2C2E;
                color: #8E8E93;
                border: 1px solid #48484A;
                border-radius: 8px;
                font: 13px ".AppleSystemUIFont";
                font-weight: 500;
                padding: 6px 12px;
            }
        """)
        
        esc_layout.addWidget(esc_label)
        esc_layout.addWidget(self.esc_display)
        esc_layout.addStretch()
        card_layout.addLayout(esc_layout)

        # Language setting
        language_layout = QtWidgets.QHBoxLayout()
        language_label = QtWidgets.QLabel("Language")
        language_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
                border: none;
                background: transparent;
            }
        """)
        language_label.setFixedWidth(140)
        
        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.addItems(list(supported_languages.keys()))
        self.language_combo.setCurrentText(self.current_language)
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        self.language_combo.setFixedSize(180, 32)
        self.language_combo.setStyleSheet("""
            QComboBox {
                background-color: #3A3A3C;
                color: #FFFFFF;
                border: 1px solid #48484A;
                border-radius: 8px;
                padding: 8px 16px;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }
            QComboBox:hover {
                background-color: #48484A;
                border: 1px solid #5A5A5C;
            }
            QComboBox:focus {
                background-color: #48484A;
                border: 1px solid #007AFF;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(caret-vertical.svg);
                border: none;
                width: 12px;
                height: 12px;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2C2C2E;
                border: 1px solid #3A3A3C;
                border-radius: 12px;
                selection-background-color: #007AFF;
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                height: 28px;
                padding: 4px 12px;
                border-radius: 6px;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007AFF;
            }
        """)
        
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        card_layout.addLayout(language_layout)

        # Microphone setting
        mic_layout = QtWidgets.QHBoxLayout()
        mic_label = QtWidgets.QLabel("Microphone")
        mic_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
                border: none;
                background: transparent;
            }
        """)
        mic_label.setFixedWidth(140)
        
        self.mic_combo = QtWidgets.QComboBox()
        self._populate_microphones()
        self.mic_combo.currentTextChanged.connect(self.on_microphone_changed)
        self.mic_combo.setFixedSize(180, 32)
        self.mic_combo.setStyleSheet("""
            QComboBox {
                background-color: #3A3A3C;
                color: #FFFFFF;
                border: 1px solid #48484A;
                border-radius: 8px;
                padding: 8px 16px;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }
            QComboBox:hover {
                background-color: #48484A;
                border: 1px solid #5A5A5C;
            }
            QComboBox:focus {
                background-color: #48484A;
                border: 1px solid #007AFF;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(caret-vertical.svg);
                border: none;
                width: 12px;
                height: 12px;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2C2C2E;
                border: 1px solid #3A3A3C;
                border-radius: 12px;
                selection-background-color: #007AFF;
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                height: 28px;
                padding: 4px 12px;
                border-radius: 6px;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007AFF;
            }
        """)
        
        mic_layout.addWidget(mic_label)
        mic_layout.addWidget(self.mic_combo)
        mic_layout.addStretch()
        card_layout.addLayout(mic_layout)

        # Space at end setting
        space_layout = QtWidgets.QHBoxLayout()
        space_label = QtWidgets.QLabel("Space at end")
        space_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
                border: none;
                background: transparent;
            }
        """)
        space_label.setFixedWidth(140)
        
        self.space_toggle = SlidingToggle()
        self.space_toggle.setChecked(self.space_at_end)
        self.space_toggle.toggled.connect(self.on_space_toggle_changed)
        
        space_layout.addWidget(space_label)
        space_layout.addWidget(self.space_toggle)
        space_layout.addStretch()
        card_layout.addLayout(space_layout)

        # Play recording sounds setting
        sounds_layout = QtWidgets.QHBoxLayout()
        sounds_label = QtWidgets.QLabel("Play recording sounds")
        sounds_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
                border: none;
                background: transparent;
            }
        """)
        sounds_label.setFixedWidth(140)
        
        self.sounds_toggle = SlidingToggle()
        self.sounds_toggle.setChecked(self.play_recording_sounds)
        self.sounds_toggle.toggled.connect(self.on_sounds_toggle_changed)
        
        sounds_layout.addWidget(sounds_label)
        sounds_layout.addWidget(self.sounds_toggle)
        sounds_layout.addStretch()
        card_layout.addLayout(sounds_layout)

        # License key setting
        license_layout = QtWidgets.QHBoxLayout()
        license_label = QtWidgets.QLabel("License key")
        license_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
                border: none;
                background: transparent;
            }
        """)
        license_label.setFixedWidth(140)
        
        self.license_input = QtWidgets.QLineEdit()
        self.license_input.setText(self.license_key)
        self.license_input.textChanged.connect(self.on_license_key_changed)
        self.license_input.setFixedSize(180, 32)
        self.license_input.setStyleSheet("""
            QLineEdit {
                background-color: #2C2C2E;
                color: #FFFFFF;
                border: 1px solid #48484A;
                border-radius: 8px;
                padding: 6px 12px;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }
            QLineEdit:hover {
                border: 1px solid #5A5A5C;
            }
            QLineEdit:focus {
                border: 1px solid #007AFF;
                background-color: #2C2C2E;
            }
            QLineEdit::placeholder {
                color: #8E8E93;
                font: 13px ".AppleSystemUIFont";
            }
        """)
        
        license_layout.addWidget(license_label)
        license_layout.addWidget(self.license_input)
        license_layout.addStretch()
        card_layout.addLayout(license_layout)

        # Add the card widget to the main layout
        main_layout.addWidget(card_widget)

    def _create_traffic_lights(self):
        """Create Apple traffic lights in the top left corner"""
        traffic_light_size = 12
        traffic_light_spacing = 8
        traffic_light_y = BUTTON_MARGIN
        
        # Red (close) button
        self.close_button = QtWidgets.QPushButton("", self)
        self.close_button.setFixedSize(traffic_light_size, traffic_light_size)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #CC4A3F;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #FF5F57;
            }
            QPushButton:pressed {
                background-color: #E0443E;
            }
        """)
        self.close_button.clicked.connect(self.close)
        self.close_button.move(BUTTON_MARGIN, traffic_light_y)
        
        # Yellow (minimize) button
        self.minimize_button = QtWidgets.QPushButton("", self)
        self.minimize_button.setFixedSize(traffic_light_size, traffic_light_size)
        self.minimize_button.setStyleSheet("""
            QPushButton {
                background-color: #CC9524;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #FFBD2E;
            }
            QPushButton:pressed {
                background-color: #E6A827;
            }
        """)
        self.minimize_button.clicked.connect(self.showMinimized)
        self.minimize_button.move(BUTTON_MARGIN + traffic_light_size + traffic_light_spacing, traffic_light_y)
        
        # Green (maximize) button
        self.maximize_button = QtWidgets.QPushButton("", self)
        self.maximize_button.setFixedSize(traffic_light_size, traffic_light_size)
        self.maximize_button.setStyleSheet("""
            QPushButton {
                background-color: #20A035;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #28CA42;
            }
            QPushButton:pressed {
                background-color: #23A838;
            }
        """)
        self.maximize_button.clicked.connect(self.toggle_maximize)
        self.maximize_button.move(BUTTON_MARGIN + (traffic_light_size + traffic_light_spacing) * 2, traffic_light_y)


    def _populate_microphones(self):
        """Populate microphone dropdown with available devices"""
        try:
            audio = pyaudio.PyAudio()
            info = audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            
            microphones = ["Default"]
            for i in range(num_devices):
                device_info = audio.get_device_info_by_host_api_device_index(0, i)
                if device_info.get('maxInputChannels') > 0:
                    microphones.append(device_info.get('name'))
            
            self.mic_combo.clear()
            self.mic_combo.addItems(microphones)
            audio.terminate()
        except Exception as e:
            print(f"Error getting microphones: {e}")
            self.mic_combo.addItems(["Default"])

    def toggle_key_recording(self):
        """Toggle between recording and displaying key"""
        if not self.is_recording_key:
            self.is_recording_key = True
            self.hotkey_button.setText("Press key")
            self.hotkey_button.setStyleSheet("""
                QPushButton {
                    background-color: #3A3A3C;
                    color: white;
                    border: 1px solid #48484A;
                    border-radius: 8px;
                    font: 13px ".AppleSystemUIFont";
                    font-weight: 500;
                    padding: 0px 16px;
                }
                QPushButton:hover {
                    background-color: #48484A;
                    border: 1px solid #5A5A5C;
                }
                QPushButton:pressed {
                    background-color: #5A5A5C;
                    border: 1px solid #6A6A6C;
                }
            """)
            self.setFocus()
        else:
            self.is_recording_key = False
            self.hotkey_button.setText(self.current_hotkey)
            self.hotkey_button.setStyleSheet("""
                QPushButton {
                    background-color: #3A3A3C;
                    color: white;
                    border: 1px solid #48484A;
                    border-radius: 8px;
                    font: 13px ".AppleSystemUIFont";
                    font-weight: 500;
                    padding: 0px 16px;
                }
                QPushButton:hover {
                    background-color: #48484A;
                    border: 1px solid #5A5A5C;
                }
                QPushButton:pressed {
                    background-color: #5A5A5C;
                    border: 1px solid #6A6A6C;
                }
            """)

    def on_language_changed(self, language):
        """Handle language selection change"""
        self.current_language = language
        self.language_changed.emit(language)

    def on_microphone_changed(self, microphone):
        """Handle microphone selection change"""
        self.current_microphone = microphone
        self.microphone_changed.emit(microphone)

    def on_space_toggle_changed(self, checked):
        """Handle space at end toggle change"""
        self.space_at_end = checked
        self.space_toggle_changed.emit(checked)

    def on_sounds_toggle_changed(self, checked):
        """Handle play recording sounds toggle change"""
        self.play_recording_sounds = checked
        self.recording_sounds_toggle_changed.emit(checked)

    def on_license_key_changed(self, text):
        """Handle license key input change"""
        self.license_key = text
        self.license_key_changed.emit(text)

    def toggle_maximize(self):
        """Toggle between maximized and normal window state"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _setup_position(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        geom = screen.geometry()
        x = (geom.width() - W) // 2
        y = (geom.height() - H) // 2
        self.move(x, y)

    def keyPressEvent(self, event):
        """Handle key press events for hotkey recording"""
        if self.is_recording_key:
            key_text = event.text()
            if key_text:
                self.current_hotkey = key_text.upper()
            else:
                self.current_hotkey = QtGui.QKeySequence(event.key()).toString()
            
            # Update button text and emit signal
            self.hotkey_button.setText(self.current_hotkey)
            self.key_set.emit(self.current_hotkey)
            self.toggle_key_recording()  # Exit recording mode

    def mouseMoveEvent(self, event):
        x, y = event.position().x(), event.position().y()
        
        # Handle dragging
        if self.dragging and self.drag_start_position:
            delta = event.globalPosition() - self.drag_start_position
            self.move(self.x() + int(delta.x()), self.y() + int(delta.y()))
            self.drag_start_position = event.globalPosition()
            return
        
        # No need to track hover state for close button anymore
        # The QPushButton handles its own hover states

    def mousePressEvent(self, event):
        # Start dragging when clicking anywhere on the window
        # The close button handles its own clicks
        self.dragging = True
        self.drag_start_position = event.globalPosition()
    
    def mouseReleaseEvent(self, event):
        # Stop dragging when mouse is released
        self.dragging = False
        self.drag_start_position = None

    def changeEvent(self, event):
        """Handle window state changes"""
        if event.type() == QtCore.QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self.hide()
        super().changeEvent(event)

    def focusOutEvent(self, event):
        """Hide window when it loses focus"""
        # Use a timer to delay hiding to avoid hiding immediately when clicking
        QtCore.QTimer.singleShot(200, self._check_and_hide)
        super().focusOutEvent(event)

    def _check_and_hide(self):
        """Check if window should be hidden after focus loss"""
        if not self.hasFocus():
            self.hide()

    @QtCore.pyqtSlot()
    def show_settings(self):
        """Show the settings window (called from menu)"""
        self.show()
        self.raise_()
        self.activateWindow()

    @QtCore.pyqtSlot(str)
    def set_language_from_menu(self, language):
        """Update language selection from rumps menu"""
        self.current_language = language
        self.language_combo.setCurrentText(language)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Shadow
        shadow_color = QtGui.QColor(0, 0, 0, 60)
        for i in range(6):
            path = QtGui.QPainterPath()
            rect = QtCore.QRectF(0.5-i, 0.5-i, W-1+2*i, H-1+2*i)
            path.addRoundedRect(rect, RADIUS+i, RADIUS+i)
            p.fillPath(path, shadow_color)

        # Rounded pill with Apple-style dark background
        rect = QtCore.QRectF(0.5, 0.5, W-1, H-1)
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, RADIUS, RADIUS)
        gradient = QtGui.QLinearGradient(0, 0, 0, H)
        gradient.setColorAt(0, QtGui.QColor(28, 28, 30))  # Apple dark gray
        gradient.setColorAt(1, QtGui.QColor(22, 22, 24))  # Apple darker gray
        p.fillPath(path, gradient)

        # Close button is now handled by QPushButton - no need to draw it

        p.end()



def main():
    app = QtWidgets.QApplication(sys.argv)
    pill = SettingsPill()
    pill.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
