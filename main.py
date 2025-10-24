import rumps
import sys
import pygame
import threading
from pynput import keyboard
from PyQt6 import QtWidgets, QtCore
import platform

from audio_recorder import AudioRecorder
from audio_pill import AudioPill
from settings import SettingsPill
from settings_manager import SettingsManager
from utils import supported_languages


class AppIcon(rumps.App):
    def __init__(self, qt_app, pill, settings_pill, settings_manager):
        super(AppIcon, self).__init__("🤫", quit_button=None)
        self.qt_app = qt_app
        self.pill = pill
        self.settings_pill = settings_pill
        
        # Initialize settings manager and load settings
        self.settings_manager = settings_manager
        
        self.recording = False
        self.transcribing = False  # Track when transcription is in progress
        self.languages = list(supported_languages.keys())
        
        # Load settings from file
        self.language = self.settings_manager.get_setting("language")
        self.hotkey_command = self.settings_manager.get_hotkey_command()
        self.hotkey = self.settings_manager.get_hotkey_name()
        self.microphone = self.settings_manager.get_setting("microphone")
        self.space_at_end = self.settings_manager.get_setting("space_at_end")
        self.play_recording_sounds = self.settings_manager.get_setting("play_recording_sounds")
        self.license_key = self.settings_manager.get_setting("license_key")
        
        self.recorder = AudioRecorder(gain=15.0)
        self.audio_file = None
        self.is_setting_hotkey = False  # Track when user is setting hotkey
        
        # Connect settings pill signals (use lambda since AppIcon is not QObject)
        self.settings_pill.key_set.connect(lambda key: self.update_hotkey(key))
        self.settings_pill.language_changed.connect(lambda lang: self.set_language_from_settings(lang))
        self.settings_pill.microphone_changed.connect(lambda mic: self.set_microphone(mic))
        self.settings_pill.space_toggle_changed.connect(lambda checked: self.set_space_at_end(checked))
        self.settings_pill.recording_sounds_toggle_changed.connect(lambda checked: self.set_play_recording_sounds(checked))
        self.settings_pill.license_key_changed.connect(lambda key: self.set_license_key(key))
        self.settings_pill.hotkey_recording_started.connect(lambda: self.start_hotkey_setup())
        self.settings_pill.hotkey_recording_stopped.connect(lambda: self.end_hotkey_setup())

        # Menu setup
        self.language_menu = rumps.MenuItem("Language")
        self.language_items = []
        for lang in self.languages:
            item = rumps.MenuItem(lang, callback=self.set_language)
            if lang == self.language:
                item.state = 1
            self.language_items.append(item)
            self.language_menu.add(item)

        self.status_item = rumps.MenuItem(f"Hotkey: {self.hotkey}", callback=None)

        self.menu = [
            self.status_item,
            rumps.MenuItem(f"Quit key: ESC", callback=None),
            None,
            self.language_menu,
            rumps.MenuItem("Settings", callback=self.show_settings),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]

        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

        self.qt_timer = rumps.Timer(lambda _: self.qt_app.processEvents(), 0.05)
        self.qt_timer.start()
        
        # Show settings window on startup
        self.show_settings(None)

    def _qt_call(self, method):
        """Thread-safe Qt method invocation"""
        QtCore.QMetaObject.invokeMethod(
            self.pill, method, QtCore.Qt.ConnectionType.QueuedConnection
        )

    def set_language(self, sender):
        for item in self.language_items:
            item.state = 0
        sender.state = 1
        self.language = sender.title
        QtCore.QMetaObject.invokeMethod(self.settings_pill, "set_language_from_menu", QtCore.Qt.ConnectionType.QueuedConnection, QtCore.Q_ARG(str, self.language))

    def show_settings(self, _):
        """Show settings pill"""
        QtCore.QMetaObject.invokeMethod(self.settings_pill, "show_settings", QtCore.Qt.ConnectionType.QueuedConnection)

    def update_hotkey(self, key_str):
        """Update the hotkey from settings"""
        if len(key_str) > 1 and key_str[0] == 'F':
            self.hotkey_command = getattr(keyboard.Key, key_str.lower())
            self.hotkey = key_str
            hotkey_command_str = f"keyboard.Key.{key_str.lower()}"
        else:
            # For regular characters
            self.hotkey_command = keyboard.KeyCode.from_char(key_str.lower())
            self.hotkey = key_str
            hotkey_command_str = f"keyboard.KeyCode.from_char('{key_str.lower()}')"
        
        # Save to settings manager
        self.settings_manager.update_hotkey(self.hotkey, hotkey_command_str)
        self.status_item.title = f"Hotkey: {self.hotkey}"

    def set_language_from_settings(self, language):
        """Update language from settings"""
        self.language = language
        self.settings_manager.update_setting("language", language)
        # Update menu items
        for item in self.language_items:
            item.state = 0
            if item.title == language:
                item.state = 1

    def set_microphone(self, microphone):
        """Update microphone setting"""
        self.microphone = microphone
        self.settings_manager.update_setting("microphone", microphone)
        # TODO: Implement microphone switching in audio recorder
        print(f"Microphone set to: {microphone}")

    def set_space_at_end(self, enabled):
        """Update space at end setting"""
        self.space_at_end = enabled
        self.settings_manager.update_setting("space_at_end", enabled)
        print(f"Space at end: {'enabled' if enabled else 'disabled'}")

    def set_play_recording_sounds(self, enabled):
        """Update play recording sounds setting"""
        self.play_recording_sounds = enabled
        self.settings_manager.update_setting("play_recording_sounds", enabled)
        print(f"Play recording sounds: {'enabled' if enabled else 'disabled'}")

    def set_license_key(self, key):
        """Update license key setting"""
        self.license_key = key
        self.settings_manager.update_setting("license_key", key)
        print(f"License key set: {key}")
    
    def start_hotkey_setup(self):
        """Called when user starts setting up a new hotkey"""
        self.is_setting_hotkey = True
        print("🔧 Hotkey setup started - recording disabled")
    
    def end_hotkey_setup(self):
        """Called when user finishes setting up a new hotkey"""
        self.is_setting_hotkey = False
        print("✅ Hotkey setup completed - recording enabled")

    def on_key_press(self, key):
        # Don't process hotkeys when setting up a new hotkey
        if self.is_setting_hotkey:
            return
        
        # Don't allow recording if transcription is in progress
        if key == self.hotkey_command and self.transcribing:
            print("⏳ Cannot start recording - transcription in progress")
            return
            
        if key == self.hotkey_command:
            self.toggle_recording()
        elif key == keyboard.Key.esc and self.recording:
            self.cancel_recording()

    def toggle_recording(self):
        if self.recording:
            # Stop recording
            self.recording = False
            self._qt_call("stop_stream")
            
            # Unmute system audio before playing stop sound
            self.recorder.unmute_system_audio()
            # Stop the recorder and get filename
            if self.play_recording_sounds:
                self.recorder.recstop_sound.play()
            self.audio_file = self.recorder.stop_recording()
            
            # Show transcribing state
            self._qt_call("set_transcribing")
            
            # Transcribe in background thread
            threading.Thread(target=self._transcribe_audio, daemon=True).start()
        else:
            # Start recording - optimize for speed
            self.recording = True
            
            # Show UI immediately for instant feedback
            self._qt_call("show")
            self._qt_call("start_stream")
            
            # Start recording in background thread to avoid blocking
            threading.Thread(target=self._start_recording_async, daemon=True).start()
    
    def _start_recording_async(self):
        """Start recording asynchronously to avoid UI lag"""
        if self.play_recording_sounds:
            self.recorder.recstart_sound.play()
        self.recorder.start_recording()
    
    def cancel_recording(self):
        """Cancel recording without transcribing or pasting"""
        if not self.recording:
            return
            
        print("🚫 Recording cancelled by ESC key")
        self.recording = False
        self._qt_call("stop_stream")
        
        # Unmute system audio
        self.recorder.unmute_system_audio()
        
        # Stop the recorder without saving or transcribing
        self.recorder.cancel_recording()
        
        # Hide the pill immediately
        self._qt_call("hide")
    
    def _transcribe_audio(self):
        """Transcribe audio in background and hide pill when done"""
        # Set transcribing flag to prevent new recordings
        self.transcribing = True
        print("🔄 Starting transcription...")
        
        # Update status to show transcription in progress
        self.status_item.title = f"Transcribing... (Hotkey: {self.hotkey})"
        
        if self.audio_file and self.recorder.whisper_model:
            # Get the language code for the selected language
            language_code = supported_languages.get(self.language, "auto")
            transcription = self.recorder.transcribe(self.audio_file, language_code, self.space_at_end)
        
        # Clear transcribing flag when done
        self.transcribing = False
        print("✅ Transcription completed")
        
        # Restore normal status
        self.status_item.title = f"Hotkey: {self.hotkey}"
        
        self._qt_call("clear_transcribing")
        self._qt_call("hide")

    def quit_app(self, _):
        self.listener.stop()
        pygame.mixer.quit()
        self._qt_call("stop_stream")
        self._qt_call("close")
        QtCore.QMetaObject.invokeMethod(self.settings_pill, "close", QtCore.Qt.ConnectionType.QueuedConnection)
        rumps.quit_application()


if __name__ == "__main__":
    # Set up the application
    qt_app = QtWidgets.QApplication(sys.argv)
    # Hide the application from dock and application switcher
    qt_app.setQuitOnLastWindowClosed(False)
    # On macOS, try to hide from application switcher
    if platform.system() == "Darwin":
        try:
            # Try to set the application as a background agent
            from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
            app = NSApplication.sharedApplication()
            app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except ImportError:
            # If AppKit is not available, try alternative approach
            pass
    
    pill = AudioPill()
    settings_manager = SettingsManager()
    settings_pill = SettingsPill(settings_manager)
    AppIcon(qt_app, pill, settings_pill, settings_manager).run()
