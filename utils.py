import pyperclip
import pyautogui
import subprocess


def insert_text(text):
    pyperclip.copy(text)
    subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'])
    #pyautogui.hotkey('command', 'v')  # mac
    # For windows: pyautogui.hotkey("ctrl","v")
