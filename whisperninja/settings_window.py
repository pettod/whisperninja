import pyaudio
from PyQt6 import QtCore, QtGui, QtWidgets
from whisperninja.utils import supported_languages
from whisperninja.key_manager import KeyManager
from whisperninja.utils import resource_path
from whisperninja.license_manager import LicenseManager

WINDOW_WIDTH, WINDOW_HEIGHT = 425, 580
RADIUS = 15
BUTTON_MARGIN = 12
ROW_SPACING = 16
COLUMN_SPACING = 64
LEFT_COLUMN_LABEL_WIDTH = 100
COMBO_BOX_WIDTH = 180
TOGGLE_BUTTON_WIDTH = 51
RIGHT_COLUMN_LABEL_WIDTH = LEFT_COLUMN_LABEL_WIDTH + COMBO_BOX_WIDTH - TOGGLE_BUTTON_WIDTH


class SlidingToggle(QtWidgets.QWidget):
    """Custom sliding toggle widget with animated knob"""
    toggled = QtCore.pyqtSignal(bool)
    
    # Define knob_position as a Qt property for animation
    knob_position = QtCore.pyqtProperty(int, fget=lambda self: self._knob_position, fset=lambda self, value: setattr(self, '_knob_position', value) or self.update())
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(TOGGLE_BUTTON_WIDTH, 31)
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
        track_rect = QtCore.QRect(0, 0, TOGGLE_BUTTON_WIDTH, 31)
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

def sharpen_image(pixmap):
    """Apply sharpen filter to pixmap"""
    img = pixmap.toImage()
    width = img.width()
    height = img.height()
    
    # Sharpen kernel: [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]
    # This emphasizes edges for a sharper appearance
    sharpened = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32)
    
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            # Get surrounding pixels
            tl = QtGui.QColor(img.pixel(x - 1, y - 1))
            tm = QtGui.QColor(img.pixel(x, y - 1))
            tr = QtGui.QColor(img.pixel(x + 1, y - 1))
            ml = QtGui.QColor(img.pixel(x - 1, y))
            mm = QtGui.QColor(img.pixel(x, y))
            mr = QtGui.QColor(img.pixel(x + 1, y))
            bl = QtGui.QColor(img.pixel(x - 1, y + 1))
            bm = QtGui.QColor(img.pixel(x, y + 1))
            br = QtGui.QColor(img.pixel(x + 1, y + 1))
            
            # Apply sharpen kernel
            r = max(0, min(255, int(mm.red() * 5 - tm.red() - ml.red() - mr.red() - bm.red())))
            g = max(0, min(255, int(mm.green() * 5 - tm.green() - ml.green() - mr.green() - bm.green())))
            b = max(0, min(255, int(mm.blue() * 5 - tm.blue() - ml.blue() - mr.blue() - bm.blue())))
            a = mm.alpha()
            
            sharpened.setPixel(x, y, QtGui.QColor(r, g, b, a).rgba())
    
    # Copy border pixels
    for y in range(height):
        for x in range(width):
            if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                sharpened.setPixel(x, y, img.pixel(x, y))
    
    return QtGui.QPixmap.fromImage(sharpened)


class SettingsWindow(QtWidgets.QWidget):
    # Signals to emit when settings change
    key_set = QtCore.pyqtSignal(str)
    key_command_set = QtCore.pyqtSignal(object)  # Emit the actual pynput key object
    language_changed = QtCore.pyqtSignal(str)
    microphone_changed = QtCore.pyqtSignal(str)
    space_toggle_changed = QtCore.pyqtSignal(bool)
    recording_sounds_toggle_changed = QtCore.pyqtSignal(bool)
    use_tiny_model_toggle_changed = QtCore.pyqtSignal(bool)
    license_key_changed = QtCore.pyqtSignal(str)
    hotkey_recording_started = QtCore.pyqtSignal()
    hotkey_recording_stopped = QtCore.pyqtSignal()
    
    def __init__(self, settings_manager=None):
        super().__init__()
        # Use standard window with proper window controls
        self.setWindowTitle("WhisperNinja")
        self.setWindowFlags(QtCore.Qt.WindowType.Window | 
                           QtCore.Qt.WindowType.WindowCloseButtonHint |
                           QtCore.Qt.WindowType.WindowMinimizeButtonHint |
                           QtCore.Qt.WindowType.WindowMaximizeButtonHint)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._setup_position()
        
        # Set window icon
        icon_path = resource_path("whisperninja/assets/logos/whisperninja.png")
        self.setWindowIcon(QtGui.QIcon(icon_path))

        # Initialize settings from settings manager or defaults
        if settings_manager:
            self.hotkey = settings_manager.get_hotkey_name()
            self.language = settings_manager.get_setting("language")
            self.microphone = settings_manager.get_setting("microphone")
            self.space_at_end = settings_manager.get_setting("space_at_end")
            self.play_recording_sounds = settings_manager.get_setting("play_recording_sounds")
            self.use_tiny_model_for_english = settings_manager.get_setting("use_tiny_model_for_english")
            self.license_key = settings_manager.get_setting("license_key")
        else:
            # Default values if no settings manager provided
            self.hotkey = "F2"
            self.language = "Auto-detect"
            self.microphone = "Default"
            self.space_at_end = True
            self.play_recording_sounds = True
            self.use_tiny_model_for_english = False
            self.license_key = ""

        # Initialize license manager (singleton)
        self.license_manager = LicenseManager.instance()
        
        # Setup UI
        self._setup_ui()

        # Timer for repaint
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

    def _setup_ui(self):
        """Setup the main UI layout"""
        # Define icon_path early for use in combobox stylesheets
        icon_path = resource_path("whisperninja/assets/icons/caret-vertical.svg")
        # Create main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 12, 24, 24)
        main_layout.setSpacing(8)

        # Company logo
        logo_path = resource_path("whisperninja/assets/logos/whisperninja.png")
        logo_label = QtWidgets.QLabel()
        logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        logo_pixmap = QtGui.QPixmap(logo_path)
        # Use device pixel ratio for high-DPI displays and scale at higher resolution first for sharpness
        device_ratio = self.devicePixelRatioF()
        target_size = 160
        # Scale to 2-3x first, then downscale for better sharpness
        high_res_size = int(target_size * max(2.0, device_ratio * 1.5))
        logo_scaled = logo_pixmap.scaled(high_res_size, high_res_size, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        # Apply sharpen filter for crisper appearance
        logo_sharpened = sharpen_image(logo_scaled)
        # Then scale down to target size with SmoothTransformation
        logo_final = logo_sharpened.scaled(int(target_size * device_ratio), int(target_size * device_ratio), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        logo_final.setDevicePixelRatio(device_ratio)
        logo_label.setPixmap(logo_final)
        logo_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding-top: 0px;
            }
        """)
        main_layout.addWidget(logo_label)

        # Title
        title_label = QtWidgets.QLabel("Welcome to\nWhisperNinja")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 32px ".AppleSystemUIFont";
                font-weight: 700;
                margin-bottom: 0px;
                text-align: center;
                letter-spacing: -0.5px;
            }
        """)
        main_layout.addWidget(title_label)

        # Create card container for all settings
        card_widget = QtWidgets.QWidget()
        card_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #141416, 
                    stop:0.5 #121214, 
                    stop:1 #0E0E10);
                border: 1px solid #2A2A2C;
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
                font: 18px ".AppleSystemUIFont";
                font-weight: 600;
                border: none;
                text-align: center;
                padding: 7px;
                letter-spacing: 0.5px;
                text-transform: uppercase;
                background: transparent;
            }
        """)
        settings_title_layout.addWidget(settings_title_label)
        card_layout.addLayout(settings_title_layout)

        # Create two-column grid layout
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setVerticalSpacing(ROW_SPACING)
        grid_layout.setHorizontalSpacing(COLUMN_SPACING)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        # Column 0: List elements
        # Row 0: Hotkey setting
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
        hotkey_label.setFixedWidth(LEFT_COLUMN_LABEL_WIDTH)
        
        self.hotkey_combo = QtWidgets.QComboBox()
        self.hotkey_combo.addItems(KeyManager.get_available_hotkeys())
        self.hotkey_combo.setCurrentText(self.hotkey)
        self.hotkey_combo.currentTextChanged.connect(self.on_hotkey_changed)
        self.hotkey_combo.setMinimumHeight(32)
        self.hotkey_combo.setFixedWidth(COMBO_BOX_WIDTH)
        self.hotkey_combo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.hotkey_combo.setStyleSheet(f"""
            QComboBox {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2A2A2E, 
                    stop:1 #1E1E22);
                color: #E0E0E0;
                border: 1px solid #3A3A3E;
                border-radius: 8px;
                padding: 8px 16px;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }}
            QComboBox:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #3A3A3E, 
                    stop:1 #2A2A2E);
                border: 1px solid #4A4A4E;
            }}
            QComboBox:focus {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #3A3A3E, 
                    stop:1 #2A2A2E);
                border: 1px solid #007AFF;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: url({icon_path});
                border: none;
                width: 12px;
                height: 12px;
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2C2C2E;
                border: 1px solid #3A3A3C;
                border-radius: 12px;
                selection-background-color: #007AFF;
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                height: 28px;
                padding: 4px 12px;
                border-radius: 6px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #007AFF;
            }}
        """)
        
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_combo, 1)
        grid_layout.addLayout(hotkey_layout, 0, 0)

        # Row 1: ESC key setting (non-editable, gray)
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
        esc_label.setFixedWidth(LEFT_COLUMN_LABEL_WIDTH)
        
        self.esc_display = QtWidgets.QLabel("ESC")
        self.esc_display.setMinimumHeight(32)
        self.esc_display.setFixedWidth(COMBO_BOX_WIDTH)
        self.esc_display.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.esc_display.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
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
        esc_layout.addWidget(self.esc_display, 1)
        grid_layout.addLayout(esc_layout, 1, 0)

        # Row 2: Language setting
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
        language_label.setFixedWidth(LEFT_COLUMN_LABEL_WIDTH)
        
        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.addItems(list(supported_languages.keys()))
        self.language_combo.setCurrentText(self.language)
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        self.language_combo.setMinimumHeight(32)
        self.language_combo.setFixedWidth(COMBO_BOX_WIDTH)
        self.language_combo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.language_combo.setStyleSheet(f"""
            QComboBox {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2A2A2E, 
                    stop:1 #1E1E22);
                color: #E0E0E0;
                border: 1px solid #3A3A3E;
                border-radius: 8px;
                padding: 8px 16px;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }}
            QComboBox:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #3A3A3E, 
                    stop:1 #2A2A2E);
                border: 1px solid #4A4A4E;
            }}
            QComboBox:focus {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #3A3A3E, 
                    stop:1 #2A2A2E);
                border: 1px solid #007AFF;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: url({icon_path});
                border: none;
                width: 12px;
                height: 12px;
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2C2C2E;
                border: 1px solid #3A3A3C;
                border-radius: 12px;
                selection-background-color: #007AFF;
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                height: 28px;
                padding: 4px 12px;
                border-radius: 6px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #007AFF;
            }}
        """)
        
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo, 1)
        grid_layout.addLayout(language_layout, 2, 0)

        # Row 3: Microphone setting
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
        mic_label.setFixedWidth(LEFT_COLUMN_LABEL_WIDTH)
        
        self.mic_combo = QtWidgets.QComboBox()
        self._populate_microphones()
        self.mic_combo.currentTextChanged.connect(self.on_microphone_changed)
        self.mic_combo.setMinimumHeight(32)
        self.mic_combo.setFixedWidth(COMBO_BOX_WIDTH)
        self.mic_combo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.mic_combo.setStyleSheet(f"""
            QComboBox {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2A2A2E, 
                    stop:1 #1E1E22);
                color: #E0E0E0;
                border: 1px solid #3A3A3E;
                border-radius: 8px;
                padding: 8px 16px;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }}
            QComboBox:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #3A3A3E, 
                    stop:1 #2A2A2E);
                border: 1px solid #4A4A4E;
            }}
            QComboBox:focus {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #3A3A3E, 
                    stop:1 #2A2A2E);
                border: 1px solid #007AFF;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: url({icon_path});
                border: none;
                width: 12px;
                height: 12px;
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2C2C2E;
                border: 1px solid #3A3A3C;
                border-radius: 12px;
                selection-background-color: #007AFF;
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                height: 28px;
                padding: 4px 12px;
                border-radius: 6px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #007AFF;
            }}
        """)
        
        mic_layout.addWidget(mic_label)
        mic_layout.addWidget(self.mic_combo, 1)
        grid_layout.addLayout(mic_layout, 3, 0)

        # Column 1: Toggle buttons
        # Row 0: Space at end setting
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
        space_label.setFixedWidth(RIGHT_COLUMN_LABEL_WIDTH)
        
        self.space_toggle = SlidingToggle()
        self.space_toggle.setChecked(self.space_at_end)
        self.space_toggle.toggled.connect(self.on_space_toggle_changed)
        
        space_layout.addWidget(space_label)
        space_layout.addStretch()
        space_layout.addWidget(self.space_toggle)
        grid_layout.addLayout(space_layout, 0, 1)

        # Row 1: Play recording sounds setting
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
        sounds_label.setFixedWidth(RIGHT_COLUMN_LABEL_WIDTH)
        
        self.sounds_toggle = SlidingToggle()
        self.sounds_toggle.setChecked(self.play_recording_sounds)
        self.sounds_toggle.toggled.connect(self.on_sounds_toggle_changed)
        
        sounds_layout.addWidget(sounds_label)
        sounds_layout.addStretch()
        sounds_layout.addWidget(self.sounds_toggle)
        grid_layout.addLayout(sounds_layout, 1, 1)

        # Row 2: Use TinyModel for English setting
        tiny_model_layout = QtWidgets.QHBoxLayout()
        tiny_model_label = QtWidgets.QLabel("Tiny English model")
        tiny_model_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 8px 0px;
                border: none;
                background: transparent;
            }
        """)
        tiny_model_label.setFixedWidth(RIGHT_COLUMN_LABEL_WIDTH)
        
        self.tiny_model_toggle = SlidingToggle()
        self.tiny_model_toggle.setChecked(self.use_tiny_model_for_english)
        self.tiny_model_toggle.toggled.connect(self.on_tiny_model_toggle_changed)
        
        tiny_model_layout.addWidget(tiny_model_label)
        tiny_model_layout.addStretch()
        tiny_model_layout.addWidget(self.tiny_model_toggle)
        grid_layout.addLayout(tiny_model_layout, 2, 1)

        # License key setting at the bottom, spanning both columns
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
        license_label.setFixedWidth(LEFT_COLUMN_LABEL_WIDTH)
        
        self.license_input = QtWidgets.QLineEdit()
        self.license_input.setText(self.license_key)
        self.license_input.textChanged.connect(self.on_license_key_changed)
        # Prevent automatic focus - only focus when user clicks
        self.license_input.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)
        self.license_input.setMinimumHeight(32)
        self.license_input.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.license_input.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1A1A1E, 
                    stop:1 #0E0E12);
                color: #E0E0E0;
                border: 1px solid #2A2A2E;
                border-radius: 8px;
                padding: 6px 12px;
                font: 13px ".AppleSystemUIFont";
                font-weight: normal;
            }
            QLineEdit:hover {
                border: 1px solid #3A3A3E;
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
        
        self.activate_button = QtWidgets.QPushButton("Activate")
        self.activate_button.setFixedSize(100, 32)
        self.activate_button.clicked.connect(self.on_activate_button_clicked)
        self.activate_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #007AFF, 
                    stop:1 #0051D5);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                font: 13px ".AppleSystemUIFont";
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0088FF, 
                    stop:1 #0060E5);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0051D5, 
                    stop:1 #003FA0);
            }
        """)
        
        license_layout.addWidget(license_label)
        license_layout.addWidget(self.license_input, 1)
        license_layout.addWidget(self.activate_button)
        # Add license row to grid layout spanning both columns (row 4, columns 0-1)
        grid_layout.addLayout(license_layout, 4, 0, 1, 2)
        
        # License status label row below license key
        license_status_layout = QtWidgets.QHBoxLayout()
        license_status_layout.setContentsMargins(0, 0, 0, 0)
        license_status_layout.addSpacing(25 + LEFT_COLUMN_LABEL_WIDTH)  # Align with license input field

        license_status_text = "Your trial expires in 7 days"
        text_color = "#FFD700"
        self.license_status = QtWidgets.QLabel(license_status_text)
        self.license_status.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font: 12px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 0px 0px;
                border: none;
                background: transparent;
            }}
        """)
        license_status_layout.addWidget(self.license_status)
        license_status_layout.addStretch()
        
        # Add license status row to grid layout spanning both columns (row 5, columns 0-1)
        grid_layout.addLayout(license_status_layout, 5, 0, 1, 2)

        # Add grid layout to card
        card_layout.addLayout(grid_layout)

        # Add the card widget to the main layout
        main_layout.addWidget(card_widget)
        
        # Update license status on initialization
        self.update_license_status()
        
        # Install event filters after UI is fully set up
        # self.language_combo.installEventFilter(self)
        # self.mic_combo.installEventFilter(self)
    
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
            
            # Set the current selection to the loaded microphone value
            if self.microphone in microphones:
                self.mic_combo.setCurrentText(self.microphone)
            else:
                # If the loaded microphone is not available, use Default
                self.mic_combo.setCurrentText("Default")
                self.microphone = "Default"
            
            audio.terminate()
        except Exception as e:
            print(f"Error getting microphones: {e}")
            self.mic_combo.addItems(["Default"])
            self.mic_combo.setCurrentText("Default")

    def on_hotkey_changed(self, hotkey_text):
        """Handle hotkey selection change from combo box"""
        self.hotkey = hotkey_text
        
        # Convert to pynput key object using VK keycodes
        key_manager = KeyManager()
        pynput_key = key_manager.hotkey_string_to_pynput(hotkey_text)
        
        # Emit signals with both name and pynput object
        self.key_set.emit(hotkey_text)
        self.key_command_set.emit(pynput_key)

    def on_language_changed(self, language):
        """Handle language selection change"""
        self.language = language
        self.language_changed.emit(language)

    def on_microphone_changed(self, microphone):
        """Handle microphone selection change"""
        self.microphone = microphone
        self.microphone_changed.emit(microphone)

    def on_space_toggle_changed(self, checked):
        """Handle space at end toggle change"""
        self.space_at_end = checked
        self.space_toggle_changed.emit(checked)

    def on_sounds_toggle_changed(self, checked):
        """Handle play recording sounds toggle change"""
        self.play_recording_sounds = checked
        self.recording_sounds_toggle_changed.emit(checked)

    def on_tiny_model_toggle_changed(self, checked):
        """Handle use TinyModel for English toggle change"""
        self.use_tiny_model_for_english = checked
        self.use_tiny_model_toggle_changed.emit(checked)

    def on_license_key_changed(self, text):
        """Handle license key input change"""
        self.license_key = text
        self.license_key_changed.emit(text)
    
    def on_activate_button_clicked(self):
        """Handle activate button click"""
        license_key = self.license_input.text().strip()
        
        if not license_key:
            # Show error message
            self.license_status.setText("Please enter a license key")
            self.license_status.setStyleSheet("""
                QLabel {
                    color: #FF3B30;
                    font: 12px ".AppleSystemUIFont";
                    font-weight: normal;
                    padding: 0px 0px;
                    border: none;
                    background: transparent;
                }
            """)
            return
        
        # Disable button during activation
        self.activate_button.setEnabled(False)
        self.activate_button.setText("Activating...")
        
        # Activate license
        success, message = self.license_manager.activate_license(license_key)
        
        # Re-enable button
        self.activate_button.setEnabled(True)
        self.activate_button.setText("Activate")
        
        # Update license status
        self.update_license_status()
        
        # Show result message
        if success:
            self.license_status.setText(message)
            self.license_status.setStyleSheet("""
                QLabel {
                    color: #34C759;
                    font: 12px ".AppleSystemUIFont";
                    font-weight: normal;
                    padding: 0px 0px;
                    border: none;
                    background: transparent;
                }
            """)
        else:
            self.license_status.setText(message)
            self.license_status.setStyleSheet("""
                QLabel {
                    color: #FF3B30;
                    font: 12px ".AppleSystemUIFont";
                    font-weight: normal;
                    padding: 0px 0px;
                    border: none;
                    background: transparent;
                }
            """)
    
    def update_license_status(self):
        """Update the license status label with current status"""
        status = self.license_manager.get_license_status()
        
        # Update label text
        self.license_status.setText(status["message"])
        
        # Update color based on status
        if status["active"]:
            # Green for active license
            color = "#34C759"
        elif status["trial_expired"]:
            # Red for expired trial
            color = "#FF3B30"
        else:
            # Yellow for trial period
            color = "#FFD700"
        
        self.license_status.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font: 12px ".AppleSystemUIFont";
                font-weight: normal;
                padding: 0px 0px;
                border: none;
                background: transparent;
            }}
        """)

    def _setup_position(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        geom = screen.geometry()
        x = (geom.width() - WINDOW_WIDTH) // 2
        y = (geom.height() - WINDOW_HEIGHT) // 2
        self.move(x, y)

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == QtCore.Qt.Key.Key_Escape:
            # Allow closing with Escape key
            self.hide()
        else:
            # Pass all other key events to the base class to handle properly
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            # Right-click to close the window
            self.hide()
        else:
            # Clear focus from license input when clicking elsewhere
            if self.license_input.hasFocus():
                self.license_input.clearFocus()
                # Set focus to the main window to ensure license field loses focus
                self.setFocus()
                # Use a timer to ensure focus is cleared
                QtCore.QTimer.singleShot(10, lambda: self.license_input.clearFocus())

    def changeEvent(self, event):
        """Handle window state changes"""
        if event.type() == QtCore.QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self.hide()
        super().changeEvent(event)

    def focusOutEvent(self, event):
        """Don't auto-hide on focus loss - let user control when to close"""
        # Just pass the event through without auto-hiding
        super().focusOutEvent(event)

    @QtCore.pyqtSlot()
    def show_settings(self):
        """Show the settings window (called from menu)"""
        self.show()
        self.raise_()
        self.activateWindow()
        # Update license status when window is shown
        self.update_license_status()
        # Ensure license input doesn't get focus automatically
        self.license_input.clearFocus()
        # Set focus to the main window instead
        self.setFocus()
        # Use a timer to ensure focus is cleared after window is fully shown
        QtCore.QTimer.singleShot(50, lambda: self.license_input.clearFocus())

    @QtCore.pyqtSlot(str)
    def set_language_from_menu(self, language):
        """Update language selection from rumps menu"""
        self.language = language
        self.language_combo.setCurrentText(language)
    
    @QtCore.pyqtSlot(str)
    def set_microphone_from_fallback(self, microphone):
        """Update microphone selection from fallback"""
        self.microphone = microphone
        self.mic_combo.setCurrentText(microphone)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Shadow
        shadow_color = QtGui.QColor(0, 0, 0, 60)
        for i in range(6):
            path = QtGui.QPainterPath()
            rect = QtCore.QRectF(0.5-i, 0.5-i, WINDOW_WIDTH-1+2*i, WINDOW_HEIGHT-1+2*i)
            path.addRoundedRect(rect, RADIUS+i, RADIUS+i)
            p.fillPath(path, shadow_color)

        # Completely black background - use actual window size for perfect scaling
        window_width = self.width()
        window_height = self.height()
        rect = QtCore.QRectF(0.5, 0.5, window_width-1, window_height-1)
        path = QtGui.QPainterPath()
        path.addRect(rect)
        p.fillPath(path, QtGui.QColor(0, 0, 0))  # Pure black
        
        # Bright dark blue gradient behind content area - use actual window size
        content_rect = QtCore.QRectF(0.5, 0.5, window_width-1, window_height-1)  # Full window area
        content_path = QtGui.QPainterPath()
        content_path.addRoundedRect(content_rect, RADIUS, RADIUS)
        
        # Radial gradient
        center_x = content_rect.center().x()
        center_y = content_rect.center().y() + 50  # Move circle lower
        max_radius = max(content_rect.width(), content_rect.height()) / 2
        
        radial_gradient = QtGui.QRadialGradient(center_x, center_y, max_radius)
        radial_gradient.setColorAt(0, QtGui.QColor(30, 60, 120, 180))    # Bright dark blue center
        radial_gradient.setColorAt(0.3, QtGui.QColor(20, 40, 80, 120))   # Medium blue
        radial_gradient.setColorAt(0.6, QtGui.QColor(10, 20, 40, 60))    # Dark blue
        radial_gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 0))          # Transparent at edges
        p.fillPath(content_path, radial_gradient)

        # Close button is now handled by QPushButton - no need to draw it

        p.end()
