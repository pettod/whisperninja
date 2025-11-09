import time
import subprocess
import sys


def _run_permission_helper(action: str) -> int:
    if action == "input-monitoring":
        try:
            from pynput import keyboard

            listener = keyboard.Listener(on_press=lambda _: None)
            listener.start()
            time.sleep(0.2)
            listener.stop()
            return 0
        except Exception as exc:
            print(f"Permission helper error (input monitoring): {exc}")
            return 1
    if action == "microphone":
        try:
            import pyaudio

            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
            stream.read(1024, exception_on_overflow=False)
            stream.stop_stream()
            stream.close()
            pa.terminate()
            return 0
        except Exception as exc:
            print(f"Permission helper error (microphone): {exc}")
            return 1
    if action == "accessibility":
        try:
            subprocess.run([
                "osascript",
                "-e",
                'tell application "System Events" to keystroke ""'
            ], check=False)
            return 0
        except Exception as exc:
            print(f"Permission helper error (accessibility): {exc}")
            return 1
    print(f"Unknown permission helper action: {action}")
    return 1


def _maybe_handle_permission_helper() -> bool:
    for arg in sys.argv[1:]:
        if arg.startswith("--permission-helper="):
            action = arg.split("=", 1)[1]
            exit_code = _run_permission_helper(action)
            sys.exit(exit_code)
    return False