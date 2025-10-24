import json
import os
import pyaudio
from pynput import keyboard


class SettingsManager:
    """Manages loading and saving of application settings"""
    
    def __init__(self, settings_file="settings.json"):
        self.settings_file = settings_file
        self.default_settings = {
            "hotkey": "F2",
            "hotkey_command": "keyboard.Key.f2",
            "language": "Automatic detection",
            "microphone": "Default",
            "space_at_end": True,
            "play_recording_sounds": True,
            "license_key": ""
        }
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from JSON file, create default if not exists"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                # Validate and fix settings
                settings = self._validate_settings(settings)
                return settings
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading settings: {e}")
                return self._create_default_settings()
        else:
            return self._create_default_settings()
    
    def save_settings(self, settings=None):
        """Save settings to JSON file"""
        if settings:
            self.settings = settings
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def _validate_settings(self, settings):
        """Validate and fix settings"""
        # Ensure all required keys exist
        for key, default_value in self.default_settings.items():
            if key not in settings:
                settings[key] = default_value
        
        # Validate microphone exists
        if not self._microphone_exists(settings.get("microphone", "Default")):
            print(f"Microphone '{settings['microphone']}' not found, using default")
            settings["microphone"] = "Default"
        
        return settings
    
    def _microphone_exists(self, microphone_name):
        """Check if the specified microphone exists"""
        if microphone_name == "Default":
            return True
        
        try:
            audio = pyaudio.PyAudio()
            info = audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            
            for i in range(num_devices):
                device_info = audio.get_device_info_by_host_api_device_index(0, i)
                if device_info.get('maxInputChannels') > 0:
                    if device_info.get('name') == microphone_name:
                        audio.terminate()
                        return True
            
            audio.terminate()
            return False
        except Exception as e:
            print(f"Error checking microphone: {e}")
            return False
    
    def _create_default_settings(self):
        """Create default settings file"""
        self.save_settings(self.default_settings)
        return self.default_settings.copy()
    
    def get_hotkey_command(self):
        """Get the hotkey command object from the stored string"""
        hotkey_command_str = self.settings.get("hotkey_command", "keyboard.Key.f2")
        
        try:
            # Parse the stored command string
            if "keyboard.Key." in hotkey_command_str:
                key_name = hotkey_command_str.split("keyboard.Key.")[1]
                return getattr(keyboard.Key, key_name)
            elif "keyboard.KeyCode.from_char" in hotkey_command_str:
                # Extract character from string like "keyboard.KeyCode.from_char('x')"
                char_start = hotkey_command_str.find("'") + 1
                char_end = hotkey_command_str.find("'", char_start)
                char = hotkey_command_str[char_start:char_end]
                return keyboard.KeyCode.from_char(char)
            else:
                # Fallback to F2
                return keyboard.Key.f2
        except Exception as e:
            print(f"Error parsing hotkey command: {e}")
            return keyboard.Key.f2
    
    def get_hotkey_name(self):
        """Get the hotkey name for display"""
        return self.settings.get("hotkey", "F2")
    
    def update_hotkey(self, hotkey_name, hotkey_command):
        """Update hotkey settings"""
        self.settings["hotkey"] = hotkey_name
        self.settings["hotkey_command"] = hotkey_command
        self.save_settings()
    
    def get_setting(self, key):
        """Get a specific setting value"""
        return self.settings.get(key, self.default_settings.get(key))
    
    def update_setting(self, key, value):
        """Update a specific setting"""
        self.settings[key] = value
        self.save_settings()
