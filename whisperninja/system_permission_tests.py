import pyaudio
import subprocess
import time
from pynput import keyboard


def test_system_permissions():
    """Test system permissions for the input monitoring, microphone, and apple events"""
    # Preflight: trigger macOS permission prompts before any window/menu shows
    try:
        # 1) Input Monitoring: briefly start a global keyboard listener
        input_listener = keyboard.Listener(on_press=lambda _: None)
        input_listener.start()
        time.sleep(0.2)
        input_listener.stop()
    except Exception:
        pass

    try:
        # 2) Microphone: open input stream briefly and read a tiny buffer
        pa = pyaudio.PyAudio()
        stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
        data = stream.read(1024, exception_on_overflow=False)
        stream.stop_stream()
        stream.close()
        pa.terminate()
    except Exception:
        pass

    try:
        # 3) Apple Events: send a benign keystroke via System Events
        # This triggers NSAppleEventsUsageDescription permission dialog
        subprocess.run([
            "osascript",
            "-e",
            'tell application "System Events" to keystroke ""'
        ], check=False)
    except Exception:
        pass