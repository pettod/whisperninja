from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush
import sys

# No external keyboard libraries - using PyQt6 native handling only

# Global key names mapping
KEY_NAMES = {
    Qt.Key.Key_Tab: "TAB",
    Qt.Key.Key_Space: "SPACE", 
    Qt.Key.Key_Return: "ENTER",
    Qt.Key.Key_Enter: "ENTER",
    Qt.Key.Key_Backspace: "BACKSPACE",
    Qt.Key.Key_Delete: "DELETE",
    Qt.Key.Key_Escape: "ESC",
    Qt.Key.Key_CapsLock: "CAPS_LOCK",
    Qt.Key.Key_Control: "CTRL",
    Qt.Key.Key_Alt: "ALT",
    Qt.Key.Key_Shift: "SHIFT",
    Qt.Key.Key_Meta: "CMD",
    Qt.Key.Key_Left: "LEFT_ARROW",
    Qt.Key.Key_Right: "RIGHT_ARROW", 
    Qt.Key.Key_Up: "UP_ARROW",
    Qt.Key.Key_Down: "DOWN_ARROW",
    Qt.Key.Key_Home: "HOME",
    Qt.Key.Key_End: "END",
    Qt.Key.Key_PageUp: "PAGE_UP",
    Qt.Key.Key_PageDown: "PAGE_DOWN",
    Qt.Key.Key_Insert: "INSERT",
    Qt.Key.Key_F1: "F1",
    Qt.Key.Key_F2: "F2",
    Qt.Key.Key_F3: "F3",
    Qt.Key.Key_F4: "F4",
    Qt.Key.Key_F5: "F5",
    Qt.Key.Key_F6: "F6",
    Qt.Key.Key_F7: "F7",
    Qt.Key.Key_F8: "F8",
    Qt.Key.Key_F9: "F9",
    Qt.Key.Key_F10: "F10",
    Qt.Key.Key_F11: "F11",
    Qt.Key.Key_F12: "F12",
}

# Demo window with native PyQt6 key handling
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("PyQt6 Sliding Toggle Example")
    
    # Add key event handling to the window
    def keyPressEvent(event):
        """Handle key press events natively in PyQt6"""
        try:
            key = event.key()
            text = event.text().upper()
            modifier = event.modifiers()
            #modifier_name = MODIFIER_NAMES.get(modifier, f"{modifier}")
            key_name = KEY_NAMES.get(key, text)
            
            print(f"{key_name}: {repr(key)}")

        except Exception as e:
            print(f"❌ Error handling key press: {e}")
    
    def keyReleaseEvent(event):
        """Handle key release events natively in PyQt6"""
        try:
            key = event.key()
            text = event.text()
            
            key_name = KEY_NAMES.get(key, f"{key}")
            
            if False:
                print(f"Key released: '{text}' ({key_name})")
                
        except Exception as e:
            print(f"❌ Error handling key release: {e}")
    
    # Bind the key event handlers
    window.keyPressEvent = keyPressEvent
    window.keyReleaseEvent = keyReleaseEvent
    
    # Enable key focus
    window.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    window.resize(150, 100)
    window.show()

    sys.exit(app.exec())
