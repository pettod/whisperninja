"""
Centralized key management for the application.
Handles all keyboard-related functionality in one place.
"""
from pynput import keyboard
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence


class KeyManager:
    """Centralized key management for the application"""
    
    def __init__(self):
        self.current_hotkey = None
        self.current_hotkey_name = "F2"
        self.listener = None
        self.is_recording_hotkey = False
        self.hotkey_callback = None
        
    def set_hotkey_callback(self, callback):
        """Set the callback function to call when hotkey is pressed"""
        self.hotkey_callback = callback
    
    def start_listener(self):
        """Start the global keyboard listener"""
        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self._on_key_press)
            self.listener.start()
    
    def stop_listener(self):
        """Stop the global keyboard listener"""
        if self.listener:
            self.listener.stop()
            self.listener = None
    
    def _on_key_press(self, key):
        """Handle key press events"""
        # Don't process hotkeys when recording a new hotkey
        if self.is_recording_hotkey:
            return
        
        # Check if the pressed key matches our hotkey
        if key == self.current_hotkey and self.hotkey_callback:
            self.hotkey_callback()
    
    def set_hotkey(self, key_obj, key_name):
        """Set the hotkey from a pynput key object"""
        self.current_hotkey = key_obj
        self.current_hotkey_name = key_name
        print(f"Hotkey set to: {key_name}")
    
    def set_hotkey_name(self, key_name):
        """Set just the hotkey name (used when updating from settings)"""
        self.current_hotkey_name = key_name
    
    def get_hotkey_name(self):
        """Get the current hotkey display name"""
        return self.current_hotkey_name
    
    def get_hotkey_object(self):
        """Get the current hotkey pynput object"""
        return self.current_hotkey
    
    def start_recording_hotkey(self):
        """Start recording mode for setting a new hotkey"""
        self.is_recording_hotkey = True
        print("🔧 Hotkey recording started")
    
    def stop_recording_hotkey(self):
        """Stop recording mode for setting a new hotkey"""
        self.is_recording_hotkey = False
        print("✅ Hotkey recording stopped")
    
    def is_hotkey_recording(self):
        """Check if currently recording a hotkey"""
        return self.is_recording_hotkey
    
    def qt_key_to_pynput(self, qt_key, text=""):
        """Convert Qt key to pynput key object"""
        # Handle regular characters
        if text and text.isprintable() and len(text) == 1:
            return keyboard.KeyCode.from_char(text)
        
        # Handle special keys
        key_mapping = {
            Qt.Key.Key_Control: keyboard.Key.ctrl,
            Qt.Key.Key_Alt: keyboard.Key.alt,
            Qt.Key.Key_Meta: keyboard.Key.cmd,
            Qt.Key.Key_Shift: keyboard.Key.shift,
            Qt.Key.Key_Space: keyboard.Key.space,
            Qt.Key.Key_Return: keyboard.Key.enter,
            Qt.Key.Key_Enter: keyboard.Key.enter,
            Qt.Key.Key_Tab: keyboard.Key.tab,
            Qt.Key.Key_Backspace: keyboard.Key.backspace,
            Qt.Key.Key_Delete: keyboard.Key.delete,
            Qt.Key.Key_Escape: keyboard.Key.esc,
            Qt.Key.Key_F1: keyboard.Key.f1,
            Qt.Key.Key_F2: keyboard.Key.f2,
            Qt.Key.Key_F3: keyboard.Key.f3,
            Qt.Key.Key_F4: keyboard.Key.f4,
            Qt.Key.Key_F5: keyboard.Key.f5,
            Qt.Key.Key_F6: keyboard.Key.f6,
            Qt.Key.Key_F7: keyboard.Key.f7,
            Qt.Key.Key_F8: keyboard.Key.f8,
            Qt.Key.Key_F9: keyboard.Key.f9,
            Qt.Key.Key_F10: keyboard.Key.f10,
            Qt.Key.Key_F11: keyboard.Key.f11,
            Qt.Key.Key_F12: keyboard.Key.f12,
        }
        
        return key_mapping.get(qt_key)
    
    def pynput_key_to_name(self, key_obj):
        """Convert pynput key object to display name"""
        if hasattr(key_obj, 'char') and key_obj.char:
            # Regular character
            return key_obj.char.upper()
        elif hasattr(key_obj, 'name'):
            # Special key (ctrl, alt, etc.)
            return key_obj.name.title()
        else:
            # Fallback
            return str(key_obj)
    
    def pynput_key_to_string(self, key_obj):
        """Convert pynput key object to string for storage"""
        if hasattr(key_obj, 'char') and key_obj.char:
            return f"keyboard.KeyCode.from_char('{key_obj.char}')"
        elif hasattr(key_obj, 'name'):
            return f"keyboard.Key.{key_obj.name}"
        else:
            return str(key_obj)
    
    def string_to_pynput_key(self, key_string):
        """Convert stored string back to pynput key object"""
        try:
            if "keyboard.KeyCode.from_char" in key_string:
                # Extract character from string like "keyboard.KeyCode.from_char('x')"
                char_start = key_string.find("'") + 1
                char_end = key_string.find("'", char_start)
                char = key_string[char_start:char_end]
                return keyboard.KeyCode.from_char(char)
            elif "keyboard.Key." in key_string:
                # Extract key name from string like "keyboard.Key.ctrl"
                key_name = key_string.split("keyboard.Key.")[1]
                return getattr(keyboard.Key, key_name)
            else:
                # Fallback to F2
                return keyboard.Key.f2
        except Exception as e:
            print(f"Error parsing key string: {e}")
            return keyboard.Key.f2
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_listener()
