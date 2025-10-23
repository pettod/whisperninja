import sys
import numpy as np
import sounddevice as sd
from PyQt6 import QtCore, QtGui, QtWidgets

W, H = 210, 40
RADIUS = 20
BAR_COUNT = 11
BAR_WIDTH = 5
BAR_GAP = 4
SMOOTHING = 0.20  # Lower = smoother motion
AMP_BASE = 15.0
AUTO_GAIN_SPEED = 0.02

# Stop button constants
STOP_BUTTON_SIZE = 20
STOP_BUTTON_X = 25  # Position on the left side
STOP_BUTTON_Y = H // 2  # Center vertically
STOP_SQUARE_SIZE = 6  # White square inside the button

# Timer constants
TIMER_X = W - 15  # Position on the right side
TIMER_Y = H // 2  # Center vertically


class AudioPill(QtWidgets.QWidget):
    def __init__(self):
        super().__init__(flags=QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(W, H)
        self._setup_position()

        self.levels = np.zeros(BAR_COUNT)
        self.audio_buffer = np.zeros(1024)
        self.gain = AMP_BASE
        
        # State management
        self.is_transcribing = False
        self.dots_count = 0
        self.is_recording = False
        self.recording_start_time = None

        # --- Precompute center weighting (middle bars stronger) ---
        indices = np.linspace(-1, 1, BAR_COUNT)
        self.center_weights = 1.0 - (indices ** 2) * 0.7  # Parabolic curve
        # Normalize weights so the peak = 1
        self.center_weights /= np.max(self.center_weights)

        # Microphone input (not started yet)
        self.stream = None

        # Update timer
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_bars)
        self.timer.start(50)

    def _setup_position(self):
        """Position window centered horizontally, bottom 10% vertically."""
        screen = QtGui.QGuiApplication.primaryScreen()
        geom = screen.geometry()
        x = (geom.width() - W) // 2
        y = int(geom.height() * 0.975) - H
        self.move(x, y)

    @QtCore.pyqtSlot()
    def start_stream(self):
        """Start listening to microphone"""
        if not self.stream:
            self.stream = sd.InputStream(
                channels=1, samplerate=44100, blocksize=1024,
                callback=self.audio_callback
            )
            self.stream.start()
            self.is_recording = True
            self.recording_start_time = QtCore.QTime.currentTime()

    @QtCore.pyqtSlot()
    def stop_stream(self):
        """Stop listening to microphone"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            self.audio_buffer = np.zeros(1024)
            self.levels = np.zeros(BAR_COUNT)
            self.is_recording = False
            self.recording_start_time = None

    @QtCore.pyqtSlot()
    def set_transcribing(self):
        """Switch to transcribing mode"""
        self.is_transcribing = True
        self.dots_count = 0

    @QtCore.pyqtSlot()
    def clear_transcribing(self):
        """Exit transcribing mode"""
        self.is_transcribing = False

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.audio_buffer = np.copy(indata[:, 0])

    def update_bars(self):
        """Convert mic signal into smoothed visual bar levels or animate dots."""
        if self.is_transcribing:
            # Animate loading dots (cycle through 0, 1, 2, 3 dots)
            self.dots_count = (self.dots_count + 1) % 20  # Slower animation
            self.update()
            return
            
        if not self.stream:
            return
            
        rms = np.sqrt(np.mean(self.audio_buffer ** 2)) + 1e-6

        # --- Auto gain control ---
        target_gain = AMP_BASE / (rms * 50 + 1e-3)
        target_gain = np.clip(target_gain, 1, 40)
        self.gain += (target_gain - self.gain) * AUTO_GAIN_SPEED

        # --- Amplify and soft-clip ---
        amplified = np.tanh(rms * self.gain * 5.0)

        # --- Apply center weighting ---
        values = np.clip(amplified * self.center_weights, 0, 1)

        # --- Smooth transitions ---
        self.levels += (values - self.levels) * SMOOTHING
        self.update()

    def draw_stop_button(self, painter):
        """Draw the red stop button with white square on the right side"""
        # Draw red circular button background
        button_rect = QtCore.QRectF(
            STOP_BUTTON_X - STOP_BUTTON_SIZE // 2,
            STOP_BUTTON_Y - STOP_BUTTON_SIZE // 2,
            STOP_BUTTON_SIZE,
            STOP_BUTTON_SIZE
        )
        
        # Red button background
        painter.setBrush(QtGui.QBrush(QtGui.QColor(220, 50, 50, 255)))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(button_rect)
        
        # Draw white square in the center
        square_rect = QtCore.QRectF(
            STOP_BUTTON_X - STOP_SQUARE_SIZE // 2,
            STOP_BUTTON_Y - STOP_SQUARE_SIZE // 2,
            STOP_SQUARE_SIZE,
            STOP_SQUARE_SIZE
        )
        
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 255)))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawRect(square_rect)

    def draw_timer(self, painter):
        """Draw the recording timer on the left side"""
        if not self.is_recording or not self.recording_start_time:
            return
            
        # Calculate elapsed time
        current_time = QtCore.QTime.currentTime()
        elapsed_ms = self.recording_start_time.msecsTo(current_time)
        elapsed_seconds = elapsed_ms // 1000
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        
        # Format time as MM:SS
        time_text = f"{minutes:02d}:{seconds:02d}"
        
        # Set font for timer
        font = QtGui.QFont(".AppleSystemUIFont", 10)
        font.setWeight(QtGui.QFont.Weight.Medium)
        painter.setFont(font)
        
        # Set text color (white)
        painter.setPen(QtGui.QColor(255, 255, 255, 255))
        
        # Draw timer text with left alignment and padding to center it better
        text_rect = QtCore.QRectF(TIMER_X - 30, TIMER_Y - 8, 50, 16)
        painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, time_text)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Rounded black background
        rect = QtCore.QRectF(0.5, 0.5, W - 1, H - 1)
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, RADIUS, RADIUS)
        p.fillPath(path, QtGui.QColor(0, 0, 0, 255))

        if self.is_transcribing:
            # Draw "Transcribing" text with loading circles below
            p.setPen(QtGui.QColor(255, 255, 255, 255))
            
            # Use Apple system font with medium weight
            font = QtGui.QFont(".AppleSystemUIFont", 11)
            font.setWeight(QtGui.QFont.Weight.Medium)
            p.setFont(font)
            
            # Draw "Transcribing" text
            text_rect = QtCore.QRectF(0, 8, W, H / 2)
            p.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop, "Transcribing")
            
            # Draw 5 loading circles below
            circle_radius = 2
            circle_spacing = 6
            circle_y = H - 12
            center_x = W / 2
            
            # Calculate which circles should be filled (0-5) - faster animation
            active_circles = (self.dots_count // 3) % 6
            
            # Draw 5 circles
            for i in range(5):
                circle_x = center_x - (2 * circle_spacing) + (i * circle_spacing)
                circle_rect = QtCore.QRectF(
                    circle_x - circle_radius, 
                    circle_y - circle_radius, 
                    circle_radius * 2, 
                    circle_radius * 2
                )
                
                if i < active_circles:
                    # Filled circle
                    p.setBrush(QtGui.QColor(255, 255, 255, 255))
                    p.setPen(QtCore.Qt.PenStyle.NoPen)
                else:
                    # Empty circle (outline only)
                    p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                    p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 100), 1))
                
                p.drawEllipse(circle_rect)
        else:
            # Draw bars
            total_width = BAR_COUNT * BAR_WIDTH + (BAR_COUNT - 1) * BAR_GAP
            start_x = (W - total_width) / 2
            base_y = H / 2

            for i, level in enumerate(self.levels):
                bx = start_x + i * (BAR_WIDTH + BAR_GAP)
                max_h = H * 0.75
                bar_h = max(3, level * max_h)
                rect = QtCore.QRectF(bx, base_y - bar_h / 2, BAR_WIDTH, bar_h)
                gradient = QtGui.QLinearGradient(0, rect.top(), 0, rect.bottom())
                gradient.setColorAt(0, QtGui.QColor(255, 255, 255, 255))
                gradient.setColorAt(1, QtGui.QColor(255, 255, 255, 90))
                p.setBrush(QtGui.QBrush(gradient))
                p.setPen(QtCore.Qt.PenStyle.NoPen)
                p.drawRoundedRect(rect, 3, 3)

        # Draw stop button
        self.draw_stop_button(p)
        
        # Draw timer
        self.draw_timer(p)

        p.end()


def main():
    app = QtWidgets.QApplication(sys.argv)
    pill = AudioPill()
    pill.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
