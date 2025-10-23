from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush
import sys

class SlidingToggle(QWidget):
    toggled = pyqtSignal(bool)  # emitted when the switch changes state

    def __init__(self, parent=None, width=60, height=28):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self._checked = False
        self._circle_pos = 3  # initial circle position
        self._animation = QPropertyAnimation(self, b"circle_pos")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    # Property to animate the circle position
    def get_circle_pos(self):
        return self._circle_pos

    def set_circle_pos(self, pos):
        self._circle_pos = pos
        self.update()

    circle_pos = property(get_circle_pos, set_circle_pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._animate()
            self.toggled.emit(self._checked)

    def _animate(self):
        start = self._circle_pos
        end = self.width() - self.height() + 3 if self._checked else 3
        self._animation.stop()
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def paintEvent(self, event):
        radius = self.height() / 2
        bg_rect = QRect(0, 0, self.width(), self.height())

        # Colors
        bg_color = QColor(0, 150, 136) if self._checked else QColor(180, 180, 180)
        circle_color = QColor(255, 255, 255)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bg_rect, radius, radius)

        # Draw sliding circle
        painter.setBrush(QBrush(circle_color))
        painter.drawEllipse(int(self._circle_pos), 3, self.height() - 6, self.height() - 6)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._animate()

# Demo window
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("PyQt6 Sliding Toggle Example")

    toggle = SlidingToggle(window)
    toggle.move(40, 40)
    toggle.toggled.connect(lambda state: print("Toggled:", state))

    window.resize(150, 100)
    window.show()
    sys.exit(app.exec())
