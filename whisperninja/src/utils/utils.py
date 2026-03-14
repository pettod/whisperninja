import os
import subprocess
import sys
import threading
import time
from pathlib import Path
import pyperclip

try:
    import pyaudio
except ImportError:
    pyaudio = None


def get_available_microphone_names():
    """Return list of microphone names for menu/settings: ['Default', ...device names]."""
    names = ["Default"]
    if pyaudio is None:
        return names
    try:
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        num_devices = info.get("deviceCount", 0)
        for i in range(num_devices):
            dev = p.get_device_info_by_host_api_device_index(0, i)
            if dev.get("maxInputChannels", 0) > 0:
                names.append(dev.get("name", ""))
        p.terminate()
    except Exception as e:
        print(f"Error getting microphones: {e}")
    return names


supported_languages = {
    "Auto-detect": None,
    "Afrikaans": "af",
    "Albanian": "sq",
    "Amharic": "am",
    "Arabic": "ar",
    "Armenian": "hy",
    "Assamese": "as",
    "Azerbaijani": "az",
    "Basque": "eu",
    "Bashkir": "ba",
    "Belarusian": "be",
    "Bengali": "bn",
    "Bosnian": "bs",
    "Breton": "br",
    "Bulgarian": "bg",
    "Catalan": "ca",
    "Cantonese": "yue",
    "Chinese": "zh",
    "Croatian": "hr",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Estonian": "et",
    "Faroese": "fo",
    "Finnish": "fi",
    "French": "fr",
    "Galician": "gl",
    "Georgian": "ka",
    "German": "de",
    "Greek": "el",
    "Gujarati": "gu",
    "Haitian Creole": "ht",
    "Hausa": "ha",
    "Hawaiian": "haw",
    "Hebrew": "he",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Icelandic": "is",
    "Indonesian": "id",
    "Italian": "it",
    "Japanese": "ja",
    "Javanese": "jw",
    "Kannada": "kn",
    "Kazakh": "kk",
    "Khmer": "km",
    "Korean": "ko",
    "Lao": "lo",
    "Latin": "la",
    "Latvian": "lv",
    "Lingala": "ln",
    "Lithuanian": "lt",
    "Luxembourgish": "lb",
    "Macedonian": "mk",
    "Malagasy": "mg",
    "Malay": "ms",
    "Malayalam": "ml",
    "Maltese": "mt",
    "Maori": "mi",
    "Marathi": "mr",
    "Mongolian": "mn",
    "Myanmar": "my",
    "Nepali": "ne",
    "Norwegian": "no",
    "Norwegian Nynorsk": "nn",
    "Occitan": "oc",
    "Pashto": "ps",
    "Persian": "fa",
    "Polish": "pl",
    "Portuguese": "pt",
    "Punjabi": "pa",
    "Romanian": "ro",
    "Russian": "ru",
    "Sanskrit": "sa",
    "Serbian": "sr",
    "Shona": "sn",
    "Sindhi": "sd",
    "Sinhala": "si",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Somali": "so",
    "Spanish": "es",
    "Sundanese": "su",
    "Swahili": "sw",
    "Swedish": "sv",
    "Tagalog": "tl",
    "Tajik": "tg",
    "Tamil": "ta",
    "Tatar": "tt",
    "Telugu": "te",
    "Thai": "th",
    "Tibetan": "bo",
    "Turkish": "tr",
    "Turkmen": "tk",
    "Ukrainian": "uk",
    "Urdu": "ur",
    "Uzbek": "uz",
    "Vietnamese": "vi",
    "Welsh": "cy",
    "Yiddish": "yi",
    "Yoruba": "yo"
}


def insert_text(text):
    # Save the current clipboard value
    previous_clipboard = pyperclip.paste()
    
    # Copy the new text and paste it immediately
    pyperclip.copy(text)
    subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'])
    #pyautogui.hotkey('command', 'v')  # mac
    # For windows: pyautogui.hotkey("ctrl","v")
    
    # Restore the previous clipboard value in a background thread after a delay
    def restore_clipboard():
        time.sleep(0.5)  # Give paste time to complete
        pyperclip.copy(previous_clipboard)
    
    threading.Thread(target=restore_clipboard, daemon=True).start()


def resource_path(relative_path):
    """Get path to resource in PyInstaller bundle or dev."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    base_dir = Path(__file__).resolve().parents[3]
    return str(base_dir / relative_path)


def user_config_path(filename):
    """
    Get path to user-writable config file in Application Support directory.
    This is the standard macOS location for app data and doesn't require special permissions.
    
    Args:
        filename: Name of the config file (e.g., "license.json", "settings.json")
    
    Returns:
        Full path to the config file in ~/Library/Application Support/WhisperNinja/
    """
    home = Path.home()
    app_support = home / "Library" / "Application Support" / "WhisperNinja"
    app_support.mkdir(parents=True, exist_ok=True)
    return str(app_support / filename)


def get_system_serial_number():
    try:
        result = subprocess.run(
            ["system_profiler", "SPHardwareDataType"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if "Serial Number (system)" in line:
                return line.split(":")[1].strip()
    except Exception as e:
        print("Error getting system serial number:", e)
    return None


def get_system_serial_number_language_independent():
    try:
        result = subprocess.run(
            ["ioreg", "-l"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if "IOPlatformSerialNumber" in line:
                # Output line looks like: "    | |   "IOPlatformSerialNumber" = "C02XXXXXXX""
                return line.split('=')[-1].strip().strip('"')
    except Exception as e:
        print("Error getting system serial number:", e)
    return None
