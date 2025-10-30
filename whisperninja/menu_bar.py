import rumps
from PyQt6 import QtCore
import threading
import pygame
from whisperninja.audio_recorder import AudioRecorder
from whisperninja.key_manager import KeyManager
from whisperninja.utils import supported_languages


class MenuBar(rumps.App):
    def __init__(self, qt_app, pill, settings_window, settings_manager):
        super(MenuBar, self).__init__("🤫", quit_button=None)
        self.qt_app = qt_app
        self.pill = pill
        self.settings_window = settings_window
        
        # Initialize settings manager and load settings
        self.settings_manager = settings_manager
        
        # Initialize key manager
        self.key_manager = KeyManager()
        self.key_manager.set_hotkey_callback(self.toggle_recording)
        
        self.recording = False
        self.transcribing = False  # Track when transcription is in progress
        self.languages = list(supported_languages.keys())
        
        # Load settings from file
        self.language = self.settings_manager.get_setting("language")
        self.microphone = self.settings_manager.get_setting("microphone")
        self.space_at_end = self.settings_manager.get_setting("space_at_end")
        self.play_recording_sounds = self.settings_manager.get_setting("play_recording_sounds")
        self.license_key = self.settings_manager.get_setting("license_key")
        
        # Load hotkey from settings
        hotkey_string = self.settings_manager.get_setting("hotkey_command")
        hotkey_obj = self.key_manager.string_to_pynput_key(hotkey_string)
        hotkey_name = self.settings_manager.get_hotkey_name()
        self.key_manager.set_hotkey(hotkey_obj, hotkey_name)
        
        self.recorder = AudioRecorder(gain=15.0)
        self.audio_file = None
        
        # Set up microphone fallback callback
        self.recorder.set_microphone_fallback_callback(self._on_microphone_fallback)
        
        # Connect settings window signals (use lambda since MenuBar is not QObject)
        self.settings_window.key_set.connect(lambda key: self.update_hotkey(key))
        self.settings_window.key_command_set.connect(lambda key_obj: self.update_hotkey_command(key_obj))
        self.settings_window.language_changed.connect(lambda lang: self.set_language_from_settings(lang))
        self.settings_window.microphone_changed.connect(lambda mic: self.set_microphone(mic))
        self.settings_window.space_toggle_changed.connect(lambda checked: self.set_space_at_end(checked))
        self.settings_window.recording_sounds_toggle_changed.connect(lambda checked: self.set_play_recording_sounds(checked))
        self.settings_window.license_key_changed.connect(lambda key: self.set_license_key(key))
        self.settings_window.hotkey_recording_started.connect(lambda: self.start_hotkey_setup())
        self.settings_window.hotkey_recording_stopped.connect(lambda: self.end_hotkey_setup())

        # Menu setup
        self.language_menu = rumps.MenuItem("Language")
        self.language_items = []
        for lang in self.languages:
            item = rumps.MenuItem(lang, callback=self.set_language)
            if lang == self.language:
                item.state = 1
            self.language_items.append(item)
            self.language_menu.add(item)

        self.status_item = rumps.MenuItem(f"Hotkey: {self.key_manager.get_hotkey_name()}", callback=None)

        self.menu = [
            self.status_item,
            rumps.MenuItem(f"Quit key: ESC", callback=None),
            None,
            self.language_menu,
            rumps.MenuItem("Settings", callback=self.show_settings),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]

        # Start the key manager listener
        self.key_manager.start_listener()

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
        QtCore.QMetaObject.invokeMethod(self.settings_window, "set_language_from_menu", QtCore.Qt.ConnectionType.QueuedConnection, QtCore.Q_ARG(str, self.language))

    def show_settings(self, _):
        """Show settings window"""
        QtCore.QMetaObject.invokeMethod(self.settings_window, "show_settings", QtCore.Qt.ConnectionType.QueuedConnection)

    def update_hotkey(self, key_str):
        """Update the hotkey from settings window"""
        # Update the key manager with the new hotkey name
        self.key_manager.set_hotkey_name(key_str)
        self.status_item.title = f"Hotkey: {key_str}"
    
    def update_hotkey_command(self, key_obj):
        """Update the hotkey command object directly from pynput"""
        # Convert pynput key object to display name
        key_name = self.key_manager.pynput_key_to_name(key_obj)
        
        # Set the hotkey in the key manager
        self.key_manager.set_hotkey(key_obj, key_name)
        
        # Save to settings
        hotkey_string = self.key_manager.pynput_key_to_string(key_obj)
        self.settings_manager.update_hotkey(key_name, hotkey_string)
        
        # Update UI
        self.status_item.title = f"Hotkey: {key_name}"

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
    
    def _on_microphone_fallback(self, fallback_microphone):
        """Called when microphone fallback occurs"""
        print(f"🔄 Updating microphone setting to: {fallback_microphone}")
        self.microphone = fallback_microphone
        self.settings_manager.update_setting("microphone", fallback_microphone)
        # Update the settings window if it's open
        QtCore.QMetaObject.invokeMethod(self.settings_window, "set_microphone_from_fallback", QtCore.Qt.ConnectionType.QueuedConnection, QtCore.Q_ARG(str, fallback_microphone))
    
    def start_hotkey_setup(self):
        """Called when user starts setting up a new hotkey"""
        self.key_manager.start_recording_hotkey()
        print("🔧 Hotkey setup started - recording disabled")
    
    def end_hotkey_setup(self):
        """Called when user finishes setting up a new hotkey"""
        self.key_manager.stop_recording_hotkey()
        print("✅ Hotkey setup completed - recording enabled")


    def toggle_recording(self):
        # Don't allow recording if transcription is in progress
        if self.transcribing:
            print("⏳ Cannot start recording - transcription in progress")
            return
            
        if self.recording:
            # Stop recording
            self.recording = False
            self._qt_call("stop_stream")
            
            # Show transcribing state IMMEDIATELY for instant UI feedback
            self._qt_call("set_transcribing")
            
            # Process audio and transcribe in background thread
            threading.Thread(target=self._process_and_transcribe_audio, daemon=True).start()
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
        self.recorder.start_recording(self.microphone)
    
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
    
    def _process_and_transcribe_audio(self):
        """Process audio and transcribe in background thread"""
        # Set transcribing flag to prevent new recordings
        self.transcribing = True
        print("🔄 Processing audio and starting transcription...")
        
        # Update status to show transcription in progress
        self.status_item.title = f"Transcribing... (Hotkey: {self.key_manager.get_hotkey_name()})"
        
        try:
            # Unmute system audio before playing stop sound
            self.recorder.unmute_system_audio()
            
            # Play stop sound if enabled
            if self.play_recording_sounds:
                self.recorder.recstop_sound.play()
            
            # Process audio (this is the heavy part that was blocking UI)
            self.audio_file = self.recorder.stop_recording()
            
            # Transcribe if we have audio file
            if self.audio_file:
                # Get the language code for the selected language
                language_code = supported_languages.get(self.language, "auto")
                transcription = self.recorder.transcribe(self.audio_file, language_code, self.space_at_end)
            
        except Exception as e:
            print(f"❌ Error during audio processing/transcription: {e}")
        finally:
            # Clear transcribing flag when done
            self.transcribing = False
            print("✅ Transcription completed")
            
            # Restore normal status
            self.status_item.title = f"Hotkey: {self.key_manager.get_hotkey_name()}"
            
            self._qt_call("clear_transcribing")
            self._qt_call("hide")

    def quit_app(self, _):
        self.key_manager.cleanup()
        pygame.mixer.quit()
        self._qt_call("stop_stream")
        self._qt_call("close")
        QtCore.QMetaObject.invokeMethod(self.settings_window, "close", QtCore.Qt.ConnectionType.QueuedConnection)
        rumps.quit_application()
