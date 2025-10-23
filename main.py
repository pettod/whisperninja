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
from utils import supported_languages


class AppIcon(rumps.App):
    def __init__(self, qt_app, pill, settings_pill):
        super(AppIcon, self).__init__("🎙️", quit_button=None)
        self.qt_app = qt_app
        self.pill = pill
        self.settings_pill = settings_pill
        self.recording = False
        self.languages = list(supported_languages.keys())
        self.current_language = "Automatic detection"
        self.hotkey = keyboard.Key.f2
        self.hotkey_name = "F2"
        self.recorder = AudioRecorder(gain=15.0)
        self.audio_file = None
        self.current_microphone = "Default"
        self.space_at_end = True
        self.license_key = ""
        
        # Connect settings pill signals (use lambda since AppIcon is not QObject)
        self.settings_pill.key_set.connect(lambda key: self.update_hotkey(key))
        self.settings_pill.language_changed.connect(lambda lang: self.set_language_from_settings(lang))
        self.settings_pill.microphone_changed.connect(lambda mic: self.set_microphone(mic))
        self.settings_pill.space_toggle_changed.connect(lambda checked: self.set_space_at_end(checked))
        self.settings_pill.license_key_changed.connect(lambda key: self.set_license_key(key))

        # Menu setup
        self.language_menu = rumps.MenuItem("Language")
        self.language_items = []
        for lang in self.languages:
            item = rumps.MenuItem(lang, callback=self.set_language)
            if lang == self.current_language:
                item.state = 1
            self.language_items.append(item)
            self.language_menu.add(item)

        self.status_item = rumps.MenuItem(f"Hotkey: {self.hotkey_name}", callback=None)

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
        self.current_language = sender.title
        QtCore.QMetaObject.invokeMethod(self.settings_pill, "set_language_from_menu", QtCore.Qt.ConnectionType.QueuedConnection, QtCore.Q_ARG(str, self.current_language))

    def show_settings(self, _):
        """Show settings pill"""
        QtCore.QMetaObject.invokeMethod(self.settings_pill, "show_settings", QtCore.Qt.ConnectionType.QueuedConnection)

    def update_hotkey(self, key_str):
        """Update the hotkey from settings"""
        if len(key_str) > 1 and key_str[0] == 'F':
            self.hotkey = getattr(keyboard.Key, key_str.lower())
            self.hotkey_name = key_str
        else:
            # For regular characters
            self.hotkey = keyboard.KeyCode.from_char(key_str.lower())
            self.hotkey_name = key_str
        self.status_item.title = f"Hotkey: {self.hotkey_name}"

    def set_language_from_settings(self, language):
        """Update language from settings"""
        self.current_language = language
        # Update menu items
        for item in self.language_items:
            item.state = 0
            if item.title == language:
                item.state = 1

    def set_microphone(self, microphone):
        """Update microphone setting"""
        self.current_microphone = microphone
        # TODO: Implement microphone switching in audio recorder
        print(f"Microphone set to: {microphone}")

    def set_space_at_end(self, enabled):
        """Update space at end setting"""
        self.space_at_end = enabled
        print(f"Space at end: {'enabled' if enabled else 'disabled'}")

    def set_license_key(self, key):
        """Update license key setting"""
        self.license_key = key
        print(f"License key set: {key}")

    def on_key_press(self, key):
        if key == self.hotkey:
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
            self.recorder.recstop_sound.play()
            self.audio_file = self.recorder.stop_recording()
            
            # Show transcribing state
            self._qt_call("set_transcribing")
            
            # Transcribe in background thread
            threading.Thread(target=self._transcribe_audio, daemon=True).start()
        else:
            # Start recording
            self.recording = True
            self.recorder.recstart_sound.play()
            self.recorder.start_recording()
            self._qt_call("start_stream")
            self._qt_call("show")
    
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
        if self.audio_file and self.recorder.whisper_model:
            # Get the language code for the selected language
            language_code = supported_languages.get(self.current_language, "auto")
            transcription = self.recorder.transcribe(self.audio_file, language_code)
            
            # Add space at end if setting is enabled
            if self.space_at_end and transcription:
                from utils import insert_text
                insert_text(transcription + " ")
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
    settings_pill = SettingsPill()
    AppIcon(qt_app, pill, settings_pill).run()
