import rumps
import threading
import time
from pynput import keyboard

class AppIcon(rumps.App):
    def __init__(self):
        super(AppIcon, self).__init__("🎙️", quit_button=None)
        self.recording = False
        self.languages = ["English", "French", "German", "Spanish"]
        self.current_language = "English"
        self.pulsing = False
        self.dictation_key = keyboard.Key.f2

        # --- Menu setup ---
        # Language submenu
        self.language_menu = rumps.MenuItem("Language")
        self.language_items = []
        for lang in self.languages:
            item = rumps.MenuItem(lang, callback=self.set_language)
            if lang == self.current_language:
                item.state = 1  # Check the current language
            self.language_items.append(item)
            self.language_menu.add(item)

        # Status item showing dictation key
        self.status_item = rumps.MenuItem(f"Press {self.dictation_key.name} to start/stop", callback=None)

        # Add items to main menu
        self.menu = [
            self.status_item,
            None,
            self.language_menu,
            None,
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]

        # Start keyboard listener
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

    def set_language(self, sender):
        # Uncheck all language items
        for item in self.language_items:
            item.state = 0
        # Check the selected language
        sender.state = 1
        self.current_language = sender.title

    def on_key_press(self, key):
        try:
            if key == self.dictation_key:
                self.toggle_recording()
        except AttributeError:
            pass

    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.recording = True
        self.pulsing = True
        threading.Thread(target=self._pulse_icon, daemon=True).start()

    def stop_recording(self):
        self.recording = False
        self.pulsing = False
        self.title = "🎙️"

    def _pulse_icon(self):
        while self.pulsing:
            self.title = "🔴"
            time.sleep(0.5)
            self.title = "🎙️"
            time.sleep(0.5)

    def quit_app(self, _):
        self.pulsing = False
        self.listener.stop()
        rumps.quit_application()

if __name__ == "__main__":
    AppIcon().run()
