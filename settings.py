import sys
from PyQt6 import QtCore, QtGui, QtWidgets

W, H = 450, 250
RADIUS = 15
CLOSE_RADIUS = 9
BUTTON_MARGIN = 12

class SettingsPill(QtWidgets.QWidget):
    # Signal to emit when key is set
    key_set = QtCore.pyqtSignal(str)
    
    def __init__(self):
        super().__init__(flags=QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(W, H)
        self._setup_position()

        self.captured_key = None
        self.prompt_text = "Press a key to set the hotkey\n\n"

        # Done button
        self.done_button = QtWidgets.QPushButton("Done", self)
        self.done_button.setFixedSize(90, 38)
        self.done_button.clicked.connect(self.on_done)
        self.done_button.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00A1FF, stop:1 #007AFF);
                color: white;
                border: none;
                border-radius: 19px;
                font: 15px ".AppleSystemUIFont";
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0090FF, stop:1 #0066CC);
            }
            QPushButton:pressed {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0066CC, stop:1 #004C99);
            }
        """)

        # Track hover state for close button
        self.close_hover = False

        self.setMouseTracking(True)

        # Timer for repaint
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

    def _setup_position(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        geom = screen.geometry()
        x = (geom.width() - W) // 2
        y = (geom.height() - H) // 2
        self.move(x, y)

    @QtCore.pyqtSlot()
    def reset_key(self):
        """Reset captured key when showing the settings"""
        self.captured_key = None
        self.update()

    def resizeEvent(self, event):
        """Position Done button"""
        self.done_button.move(W - self.done_button.width() - BUTTON_MARGIN,
                              H - self.done_button.height() - BUTTON_MARGIN)

    def keyPressEvent(self, event):
        key_text = event.text()
        if key_text:
            self.captured_key = key_text.upper()
        else:
            self.captured_key = QtGui.QKeySequence(event.key()).toString()
        self.update()

    def mouseMoveEvent(self, event):
        x, y = event.position().x(), event.position().y()
        # Check if cursor is over the close circle
        if (BUTTON_MARGIN <= x <= BUTTON_MARGIN + CLOSE_RADIUS*2 and
            BUTTON_MARGIN <= y <= BUTTON_MARGIN + CLOSE_RADIUS*2):
            self.close_hover = True
        else:
            self.close_hover = False
        self.update()

    def mousePressEvent(self, event):
        if self.close_hover:
            self.close()

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

        # Rounded pill with subtle gradient
        rect = QtCore.QRectF(0.5, 0.5, W-1, H-1)
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, RADIUS, RADIUS)
        gradient = QtGui.QLinearGradient(0, 0, 0, H)
        gradient.setColorAt(0, QtGui.QColor(30,30,30))
        gradient.setColorAt(1, QtGui.QColor(20,20,20))
        p.fillPath(path, gradient)

        # Draw text
        font = QtGui.QFont(".AppleSystemUIFont", 14)
        font.setWeight(QtGui.QFont.Weight.Medium)
        p.setFont(font)
        p.setPen(QtGui.QColor(255,255,255))
        display_text = self.prompt_text + (self.captured_key if self.captured_key else "")
        text_rect = QtCore.QRectF(20, 20, W-40, H-60)
        p.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignCenter, display_text)

        # Draw red close button
        close_rect = QtCore.QRectF(BUTTON_MARGIN, BUTTON_MARGIN, CLOSE_RADIUS*2, CLOSE_RADIUS*2)
        p.setBrush(QtGui.QColor(255, 95, 87))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.drawEllipse(close_rect)

        # Draw hover "×"
        if self.close_hover:
            p.setPen(QtGui.QColor(255,255,255))
            font = QtGui.QFont(".AppleSystemUIFont", 15)
            font.setWeight(QtGui.QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(close_rect, QtCore.Qt.AlignmentFlag.AlignCenter, "×")

        p.end()

    @QtCore.pyqtSlot()
    def on_done(self):
        if self.captured_key:
            print(f"hotkey set to: {self.captured_key}")
            self.key_set.emit(self.captured_key)
        self.close()


def main():
    app = QtWidgets.QApplication(sys.argv)
    pill = SettingsPill()
    pill.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
