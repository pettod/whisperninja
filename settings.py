import sys
import pyaudio
from PyQt6 import QtCore, QtGui, QtWidgets
from utils import supported_languages

W, H = 500, 600
RADIUS = 15
CLOSE_RADIUS = 9
BUTTON_MARGIN = 12

class SettingsPill(QtWidgets.QWidget):
    # Signals to emit when settings change
    key_set = QtCore.pyqtSignal(str)
    language_changed = QtCore.pyqtSignal(str)
    microphone_changed = QtCore.pyqtSignal(str)
    space_toggle_changed = QtCore.pyqtSignal(bool)
    license_key_changed = QtCore.pyqtSignal(str)
    
    def __init__(self):
        super().__init__(flags=QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(W, H)
        self._setup_position()

        # Initialize settings
        self.current_hotkey = "F2"
        self.current_language = "Automatic detection"
        self.current_microphone = "Default"
        self.space_at_end = False
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

        # Title
        title_label = QtWidgets.QLabel("Settings")
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 22px ".AppleSystemUIFont";
                font-weight: 600;
                margin-bottom: 8px;
            }
        """)
        main_layout.addWidget(title_label)

        # Hotkey setting
        hotkey_layout = QtWidgets.QHBoxLayout()
        hotkey_label = QtWidgets.QLabel("Hotkey")
        hotkey_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
            }
        """)
        hotkey_label.setFixedWidth(140)
        
        self.hotkey_button = QtWidgets.QPushButton("Record key")
        self.hotkey_button.setFixedSize(180, 32)
        self.hotkey_button.clicked.connect(self.toggle_key_recording)
        self.hotkey_button.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3C;
                color: white;
                border: none;
                border-radius: 16px;
                font: 13px ".AppleSystemUIFont";
                font-weight: 500;
                padding: 0px 16px;
            }
            QPushButton:hover {
                background-color: #007AFF;
            }
            QPushButton:pressed {
                background-color: #0056CC;
            }
        """)
        
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_button)
        hotkey_layout.addStretch()
        main_layout.addLayout(hotkey_layout)

        # Language setting
        language_layout = QtWidgets.QHBoxLayout()
        language_label = QtWidgets.QLabel("Language")
        language_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
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
                border: none;
                border-radius: 16px;
                padding: 8px 16px;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }
            QComboBox:hover {
                background-color: #48484A;
            }
            QComboBox:focus {
                background-color: #48484A;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #FFFFFF;
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
        main_layout.addLayout(language_layout)

        # Microphone setting
        mic_layout = QtWidgets.QHBoxLayout()
        mic_label = QtWidgets.QLabel("Microphone")
        mic_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
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
                border: none;
                border-radius: 16px;
                padding: 8px 16px;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }
            QComboBox:hover {
                background-color: #48484A;
            }
            QComboBox:focus {
                background-color: #48484A;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #FFFFFF;
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
        main_layout.addLayout(mic_layout)

        # Space at end setting
        space_layout = QtWidgets.QHBoxLayout()
        space_label = QtWidgets.QLabel("Space at end")
        space_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
            }
        """)
        space_label.setFixedWidth(140)
        
        self.space_toggle = QtWidgets.QCheckBox()
        self.space_toggle.setChecked(self.space_at_end)
        self.space_toggle.toggled.connect(self.on_space_toggle_changed)
        self.space_toggle.setFixedSize(32, 20)
        self.space_toggle.setStyleSheet("""
            QCheckBox {
                spacing: 0px;
            }
            QCheckBox::indicator {
                width: 51px;
                height: 31px;
                border-radius: 15px;
                background-color: #3A3A3C;
                border: 1px solid #48484A;
            }
            QCheckBox::indicator:checked {
                background-color: #34C759;
                border: 1px solid #34C759;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3A3A3C;
                border: 1px solid #48484A;
            }
        """)
        
        space_layout.addWidget(space_label)
        space_layout.addWidget(self.space_toggle)
        space_layout.addStretch()
        main_layout.addLayout(space_layout)

        # License key setting
        license_layout = QtWidgets.QHBoxLayout()
        license_label = QtWidgets.QLabel("License key")
        license_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
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
                border: 1px solid #3A3A3C;
                border-radius: 8px;
                padding: 6px 12px;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }
            QLineEdit:hover {
                border: 1px solid #48484A;
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
        main_layout.addLayout(license_layout)

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
                    border: none;
                    border-radius: 16px;
                    font: 13px ".AppleSystemUIFont";
                    font-weight: 500;
                    padding: 0px 16px;
                }
                QPushButton:hover {
                    background-color: #FF3B30;
                }
                QPushButton:pressed {
                    background-color: #D70015;
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
                    border: none;
                    border-radius: 16px;
                    font: 13px ".AppleSystemUIFont";
                    font-weight: 500;
                    padding: 0px 16px;
                }
                QPushButton:hover {
                    background-color: #007AFF;
                }
                QPushButton:pressed {
                    background-color: #0056CC;
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
