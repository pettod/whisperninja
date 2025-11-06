"""
Centralized key management for the application.
Handles all keyboard-related functionality in one place.
"""
from pynput import keyboard
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

# Keycode mappings for macOS (VK keycodes)
KEYCODE_CMD_LEFT = 55
KEYCODE_CMD_RIGHT = 54
KEYCODE_GLOBE = 179
KEYCODE_OPTION = 58
KEYCODE_CTRL = 62

class KeyManager:
    """Centralized key management for the application"""
    
    def __init__(self):
        self.current_hotkey = None
        self.current_hotkey_name = "F2"
        self.current_hotkey_vk = None  # Store VK keycode for matching
        self.listener = None
        self.is_recording_hotkey = False
        self.hotkey_callback = None
        self.esc_callback = None
    
    @staticmethod
    def get_available_hotkeys():
        """Get list of available hotkey options"""
        hotkeys = []
        
        # F keys from F1 to F12
        hotkeys.extend([f"F{i}" for i in range(1, 13)])
        
        # Add modifier keys as individual options
        hotkeys.extend(["⌘ Cmd (left)", "⌘ Cmd (right)", "⌥ Option", "⌃ Control", "🌐︎ Globe"])
        
        return hotkeys
    
    @staticmethod
    def _get_vk(key_obj):
        """
        Try several ways to get a virtual-key code (vk) from the key object.
        Returns int or None.
        """
        # Direct attribute (KeyCode on some platforms)
        vk = getattr(key_obj, "vk", None)
        if vk is not None:
            return vk
        # Sometimes the numeric value sits in key.value.vk
        val = getattr(key_obj, "value", None)
        if val is not None:
            vk = getattr(val, "vk", None)
            if vk is not None:
                return vk
        return None
    
    @staticmethod
    def hotkey_string_to_pynput(hotkey_string):
        """Convert hotkey string to pynput key object using VK keycodes"""
        # Map display names to VK keycodes
        vk_map = {
            "⌘ Cmd (left)": KEYCODE_CMD_LEFT,
            "⌘ Cmd (right)": KEYCODE_CMD_RIGHT,
            "⌥ Option": KEYCODE_OPTION,
            "⌃ Control": KEYCODE_CTRL,
            "🌐︎ Globe": KEYCODE_GLOBE
        }
        
        # Check if it's a modifier or special key
        if hotkey_string in vk_map:
            vk = vk_map[hotkey_string]
            return keyboard.KeyCode.from_vk(vk)
        
        # F keys are named f1, f2, etc. in pynput
        f_key_obj = getattr(keyboard.Key, hotkey_string.lower(), None)
        return f_key_obj if f_key_obj else keyboard.Key.f2
    
    @staticmethod
    def pynput_key_to_hotkey_string(key_obj):
        """Convert pynput key object to hotkey string"""
        # Check by VK keycode first for modifier keys
        vk = KeyManager._get_vk(key_obj)
        
        if vk is not None:
            vk_map = {
                KEYCODE_CMD_LEFT: '⌘ Cmd (left)',
                KEYCODE_CMD_RIGHT: '⌘ Cmd (right)',
                KEYCODE_OPTION: '⌥ Option',
                KEYCODE_CTRL: '⌃ Control',
                KEYCODE_GLOBE: '🌐︎ Globe'
            }
            if vk in vk_map:
                return vk_map[vk]
        
        if hasattr(key_obj, 'name'):
            name = key_obj.name
            
            # F keys are f1, f2, etc. in pynput, convert to F1, F2, etc.
            if name.startswith('f') and name[1:].isdigit():
                return name.upper()
        
        # Fallback to F2
        return "F2"
        
    def set_hotkey_callback(self, callback):
        """Set the callback function to call when hotkey is pressed"""
        self.hotkey_callback = callback
    
    def set_esc_callback(self, callback):
        """Set the callback function to call when ESC key is pressed"""
        self.esc_callback = callback
    
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
        """Handle key press events - matches by VK keycode"""
        # Don't process hotkeys when recording a new hotkey
        if self.is_recording_hotkey:
            return
        
        # Check for ESC key to cancel recording
        if key == keyboard.Key.esc and self.esc_callback:
            self.esc_callback()
            return
        
        # Check if the pressed key matches our hotkey using VK keycode
        if self.current_hotkey is not None:
            # Get VK keycodes for comparison
            pressed_vk = self._get_vk(key)
            stored_vk = self.current_hotkey_vk
            
            # If both have VK keycodes, compare by VK
            if pressed_vk is not None and stored_vk is not None:
                if pressed_vk == stored_vk:
                    print(f"   ✅ Match by VK keycode: {pressed_vk} == {stored_vk}")
                    if self.hotkey_callback:
                        self.hotkey_callback()
            # Check if pressed key is a Key object (like keyboard.Key.ctrl) and map to VK
            elif hasattr(key, 'name') and not pressed_vk:
                # Map Key object names to VK keycodes for comparison
                key_name_to_vk = {
                    'ctrl': KEYCODE_CTRL,
                    'alt': KEYCODE_OPTION
                }
                # Special handling for 'cmd' - can be either left or right
                if key.name == 'cmd':
                    # Accept if stored key is either left or right cmd
                    if stored_vk in (KEYCODE_CMD_LEFT, KEYCODE_CMD_RIGHT):
                        print(f"   ✅ Match by Key name mapping: {key.name} matches cmd (stored_vk: {stored_vk})")
                        if self.hotkey_callback:
                            self.hotkey_callback()
                elif key.name in key_name_to_vk:
                    mapped_vk = key_name_to_vk[key.name]
                    if stored_vk == mapped_vk:
                        print(f"   ✅ Match by Key name mapping: {key.name} -> {mapped_vk} == {stored_vk}")
                        if self.hotkey_callback:
                            self.hotkey_callback()
            # Otherwise, fall back to object equality comparison
            elif key == self.current_hotkey:
                print(f"   ✅ Match by object equality")
                if self.hotkey_callback:
                    self.hotkey_callback()
    
    def set_hotkey(self, key_obj, key_name):
        """Set the hotkey from a pynput key object"""
        self.current_hotkey = key_obj
        self.current_hotkey_name = key_name
        # Store VK keycode for matching
        self.current_hotkey_vk = self._get_vk(key_obj)
        print(f"Hotkey set to: {key_name} (VK: {self.current_hotkey_vk})")
    
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
        # Use the same logic as pynput_key_to_hotkey_string to handle VK codes
        return KeyManager.pynput_key_to_hotkey_string(key_obj)
    
    def pynput_key_to_string(self, key_obj):
        """Convert pynput key object to string for storage"""
        # Check for VK keycode first (for KeyCode objects with keycodes)
        vk = self._get_vk(key_obj)
        if vk is not None:
            # Check if it's a KeyCode object (has vk) vs a Key object
            # Key objects don't have vk attribute, so if vk exists, it's a KeyCode
            return f"keyboard.KeyCode.from_vk({vk})"
        
        # Check for Key objects (enum-like objects like keyboard.Key.ctrl)
        if hasattr(key_obj, 'name') and not hasattr(key_obj, 'char'):
            return f"keyboard.Key.{key_obj.name}"
        
        # Check for KeyCode objects with character
        if hasattr(key_obj, 'char') and key_obj.char:
            return f"keyboard.KeyCode.from_char('{key_obj.char}')"
        
        # Fallback
        return str(key_obj)
    
    def string_to_pynput_key(self, key_string):
        """Convert stored string back to pynput key object"""
        try:
            if "keyboard.KeyCode.from_vk" in key_string:
                # Extract keycode from string like "keyboard.KeyCode.from_vk(55)"
                import re
                match = re.search(r'from_vk\((\d+)\)', key_string)
                if match:
                    vk = int(match.group(1))
                    return keyboard.KeyCode.from_vk(vk)
            elif "keyboard.KeyCode.from_char" in key_string:
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
