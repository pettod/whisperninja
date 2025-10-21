import rumps
import sys
import pygame
import threading
from pynput import keyboard
from PyQt6 import QtWidgets, QtCore

from audio_recorder import AudioRecorder
from audio_pill import AudioPill


class AppIcon(rumps.App):
    def __init__(self, qt_app, pill):
        super(AppIcon, self).__init__("🎙️", quit_button=None)
        self.qt_app = qt_app
        self.pill = pill
        self.recording = False
        self.languages = ["English", "French", "German", "Spanish"]
        self.current_language = "English"
        self.dictation_key = keyboard.Key.f2
        self.recorder = AudioRecorder(gain=15.0)
        self.audio_file = None

        # Menu setup
        self.language_menu = rumps.MenuItem("Language")
        self.language_items = []
        for lang in self.languages:
            item = rumps.MenuItem(lang, callback=self.set_language)
            if lang == self.current_language:
                item.state = 1
            self.language_items.append(item)
            self.language_menu.add(item)

        self.menu = [
            rumps.MenuItem(f"Press {self.dictation_key.name} to start/stop", callback=None),
            None,
            self.language_menu,
            None,
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]

        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

        self.qt_timer = rumps.Timer(lambda _: self.qt_app.processEvents(), 0.05)
        self.qt_timer.start()

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

    def on_key_press(self, key):
        if key == self.dictation_key:
            self.toggle_recording()

    def toggle_recording(self):
        if self.recording:
            # Stop recording
            self.recording = False
            self._qt_call("stop_stream")
            
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
    
    def _transcribe_audio(self):
        """Transcribe audio in background and hide pill when done"""
        if self.audio_file and self.recorder.whisper_model:
            self.recorder.transcribe(self.audio_file)
        self._qt_call("clear_transcribing")
        self._qt_call("hide")

    def quit_app(self, _):
        self.listener.stop()
        pygame.mixer.quit()
        self._qt_call("stop_stream")
        self._qt_call("close")
        rumps.quit_application()


if __name__ == "__main__":
    qt_app = QtWidgets.QApplication(sys.argv)
    pill = AudioPill()
    AppIcon(qt_app, pill).run()
