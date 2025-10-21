import rumps

class DictationMenuApp(rumps.App):
    LANGUAGE_OPTIONS = [
        "English", "Spanish", "French", "German",
        "Italian", "Portuguese", "Chinese", "Japanese", "Korean"
    ]
    # Optionally you could add language codes for use with backends

    def __init__(self):
        super(DictationMenuApp, self).__init__("🎙️", icon=None, menu=["Language", "Dictation Key"])
        # Default selections
        self.selected_language = self.LANGUAGE_OPTIONS[0]
        self.dictation_key = ""

        # Dropdown for language
        self.language_menu = rumps.MenuItem("Language")
        self.language_dropdown = []
        for lang in self.LANGUAGE_OPTIONS:
            item = rumps.MenuItem(lang, callback=self.on_language_select)
            if lang == self.selected_language:
                item.state = 1
            self.language_dropdown.append(item)
            self.menu["Language"].add(item)

        # Form item for dictation key
        self.menu["Dictation Key"] = rumps.MenuItem(f"Current Key: {self.dictation_key}", callback=self.prompt_dictation_key)

    def on_language_select(self, sender):
        # Uncheck others, check selected
        for item in self.language_dropdown:
            item.state = 0
        sender.state = 1
        self.selected_language = sender.title
        rumps.notification("Language Changed", "", f"Selected: {self.selected_language}")

    def prompt_dictation_key(self, _):
        response = rumps.Window(
            "Enter the dictation key you want to use (e.g. Cmd+D):",
            "Dictation Key",
            default_text=self.dictation_key
        ).run()
        if response.clicked:
            self.dictation_key = response.text
            self.menu["Dictation Key"].title = f"Current Key: {self.dictation_key}"
            rumps.notification("Dictation Key Changed", "", f"Key: {self.dictation_key}")

if __name__ == "__main__":
    DictationMenuApp().run()
