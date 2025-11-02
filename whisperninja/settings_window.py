import math
import sys
import pyaudio
import random
from PyQt6 import QtCore, QtGui, QtWidgets
from whisperninja.utils import supported_languages
from whisperninja.key_manager import KeyManager
from whisperninja.utils import resource_path

W, H = 425, 760
RADIUS = 15
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
        self.resize(W, H)
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
            self.license_key = settings_manager.get_setting("license_key")
        else:
            # Default values if no settings manager provided
            self.hotkey = "F2"
            self.language = "Auto-detect"
            self.microphone = "Default"
            self.space_at_end = True
            self.play_recording_sounds = True
            self.license_key = ""
        
        self.is_recording_key = False

        # Setup UI
        self._setup_ui()

        # Timer for repaint and starfield animation
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)
        
        # Initialize starfield
        self.stars = []
        self._generate_stars()

    def _setup_ui(self):
        """Setup the main UI layout"""
        # Create main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

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
                padding-top: 20px;
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
                margin-bottom: 8px;
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
        
        self.hotkey_button = QtWidgets.QPushButton(self.hotkey)
        self.hotkey_button.setFixedSize(180, 32)
        self.hotkey_button.clicked.connect(self.toggle_key_recording)
        self.hotkey_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1E1E20, 
                    stop:1 #161618);
                color: #E0E0E0;
                border: 1px solid #2A2A2C;
                border-radius: 8px;
                font: 13px ".AppleSystemUIFont";
                font-weight: 500;
                padding: 0px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2A2A2C, 
                    stop:1 #1E1E20);
                border: 1px solid #3A3A3C;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #121214, 
                    stop:1 #0A0A0C);
                border: 1px solid #1A1A1C;
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
        
        icon_path = resource_path("whisperninja/assets/icons/caret-vertical.svg")
        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.addItems(list(supported_languages.keys()))
        self.language_combo.setCurrentText(self.language)
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        self.language_combo.setFixedSize(180, 32)
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
        # Prevent automatic focus - only focus when user clicks
        self.license_input.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)
        self.license_input.setFixedSize(180, 32)
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
        
        license_layout.addWidget(license_label)
        license_layout.addWidget(self.license_input)
        license_layout.addStretch()
        card_layout.addLayout(license_layout)

        # Add the card widget to the main layout
        main_layout.addWidget(card_widget)
        
        # Install event filters after UI is fully set up
        # self.language_combo.installEventFilter(self)
        # self.mic_combo.installEventFilter(self)
    
    def _generate_stars(self):
        """Generate random stars for the background"""
        self.stars = []
        for _ in range(25):  # Not too many stars
            star = {
                'x': random.randint(0, W),
                'y': random.randint(0, H),
                'brightness': random.uniform(0.3, 1.0),
                'twinkle_speed': random.uniform(0.02, 0.08),
                'twinkle_phase': random.uniform(0, 6.28),  # 0 to 2π
                'size': random.uniform(1, 3)
            }
            self.stars.append(star)
    
    def _update_stars(self):
        """Update star animation"""
        for star in self.stars:
            # Update twinkle phase
            star['twinkle_phase'] += star['twinkle_speed']
            if star['twinkle_phase'] > 6.28:  # 2π
                star['twinkle_phase'] = 0
            
            # Calculate brightness with sine wave for smooth twinkling
            base_brightness = 0.3
            twinkle_amount = 0.7
            star['brightness'] = base_brightness + twinkle_amount * (math.sin(star['twinkle_phase']) + 1) / 2
    
    def _draw_stars(self, painter):
        """Draw the animated starfield"""
        for star in self.stars:
            # Calculate star color based on brightness
            brightness = star['brightness']
            alpha = int(255 * brightness)
            
            # Create star color (white with varying alpha)
            star_color = QtGui.QColor(255, 255, 255, alpha)
            painter.setPen(QtGui.QPen(star_color, star['size']))
            
            # Draw star as a small circle
            painter.drawEllipse(
                int(star['x'] - star['size']/2), 
                int(star['y'] - star['size']/2), 
                int(star['size']), 
                int(star['size'])
            )
            
            # Add a subtle glow effect for brighter stars
            if brightness > 0.8:
                glow_color = QtGui.QColor(200, 220, 255, int(alpha * 0.3))
                painter.setPen(QtGui.QPen(glow_color, star['size'] * 2))
                painter.drawEllipse(
                    int(star['x'] - star['size']), 
                    int(star['y'] - star['size']), 
                    int(star['size'] * 2), 
                    int(star['size'] * 2)
                )

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

    def toggle_key_recording(self):
        """Toggle between recording and displaying key"""
        if not self.is_recording_key:
            self.is_recording_key = True
            self.hotkey_button.setText("Press key")
            # Emit signal to disable recording
            self.hotkey_recording_started.emit()
            self.hotkey_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #2A2A2E, 
                        stop:1 #1E1E22);
                    color: #E0E0E0;
                    border: 1px solid #3A3A3E;
                    border-radius: 8px;
                    font: 13px ".AppleSystemUIFont";
                    font-weight: 500;
                    padding: 0px 16px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #3A3A3E, 
                        stop:1 #2A2A2E);
                    border: 1px solid #4A4A4E;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #1A1A1E, 
                        stop:1 #0E0E12);
                    border: 1px solid #2A2A2E;
                }
            """)
            self.setFocus()
        else:
            self.is_recording_key = False
            self.hotkey_button.setText(self.hotkey)
            # Emit signal to re-enable recording
            self.hotkey_recording_stopped.emit()
            self.hotkey_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #2A2A2E, 
                        stop:1 #1E1E22);
                    color: #E0E0E0;
                    border: 1px solid #3A3A3E;
                    border-radius: 8px;
                    font: 13px ".AppleSystemUIFont";
                    font-weight: 500;
                    padding: 0px 16px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #3A3A3E, 
                        stop:1 #2A2A2E);
                    border: 1px solid #4A4A4E;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #1A1A1E, 
                        stop:1 #0E0E12);
                    border: 1px solid #2A2A2E;
                }
            """)

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

    def on_license_key_changed(self, text):
        """Handle license key input change"""
        self.license_key = text
        self.license_key_changed.emit(text)

    def _setup_position(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        geom = screen.geometry()
        x = (geom.width() - W) // 2
        y = (geom.height() - H) // 2
        self.move(x, y)

    def keyPressEvent(self, event):
        """Handle key press events for hotkey recording"""
        if self.is_recording_key:
            # Convert Qt key to pynput key object using key manager
            key_manager = KeyManager()
            pynput_key = key_manager.qt_key_to_pynput(event.key(), event.text())
            
            if pynput_key:
                # Convert to display name
                key_name = key_manager.pynput_key_to_name(pynput_key)
                
                # Update UI
                self.hotkey = key_name
                self.hotkey_button.setText(key_name)
                
                # Emit signals with both name and pynput object
                self.key_set.emit(key_name)
                self.key_command_set.emit(pynput_key)
                
                # Stop recording mode
                self.toggle_key_recording()
        elif event.key() == QtCore.Qt.Key.Key_Escape:
            # Allow closing with Escape key
            self.hide()

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
            rect = QtCore.QRectF(0.5-i, 0.5-i, W-1+2*i, H-1+2*i)
            path.addRoundedRect(rect, RADIUS+i, RADIUS+i)
            p.fillPath(path, shadow_color)

        # Completely black background
        rect = QtCore.QRectF(0.5, 0.5, W-1, H-1)
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, RADIUS, RADIUS)
        p.fillPath(path, QtGui.QColor(0, 0, 0))  # Pure black
        
        # Bright dark blue gradient behind content area
        content_rect = QtCore.QRectF(50, 50, W-100, H-200)  # Content area
        content_path = QtGui.QPainterPath()
        content_path.addRoundedRect(content_rect, RADIUS-5, RADIUS-5)
        
        # Radial gradient from center
        center_x = content_rect.center().x()
        center_y = content_rect.center().y()
        max_radius = max(content_rect.width(), content_rect.height()) / 2
        
        radial_gradient = QtGui.QRadialGradient(center_x, center_y, max_radius)
        radial_gradient.setColorAt(0, QtGui.QColor(30, 60, 120, 180))    # Bright dark blue center
        radial_gradient.setColorAt(0.3, QtGui.QColor(20, 40, 80, 120))   # Medium blue
        radial_gradient.setColorAt(0.6, QtGui.QColor(10, 20, 40, 60))    # Dark blue
        radial_gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 0))          # Transparent at edges
        p.fillPath(content_path, radial_gradient)

        # Draw animated starfield
        self._draw_stars(p)

        # Close button is now handled by QPushButton - no need to draw it

        p.end()
