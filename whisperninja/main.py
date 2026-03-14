import os
import sys
import platform
import subprocess
import signal
import threading
from PyQt6 import QtWidgets
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
from whisperninja.src.audio.audio_window import AudioWindow
from whisperninja.src.ui.settings_manager import SettingsManager
from whisperninja.src.ui.settings_window import SettingsWindow
from whisperninja.src.installation.request_permissions import RequestPermissionsDialog
from whisperninja.src.license.license_manager import LicenseManager
from whisperninja.src.installation.permissions_helper import _maybe_handle_permission_helper


def restart_application():
    python = sys.executable
    args = [python, *sys.argv]
    try:
        subprocess.Popen(args, close_fds=True)
    except Exception as exc:  # pragma: no cover - best-effort restart
        print(f"Failed to relaunch WhisperNinja automatically: {exc}")
    # Then cleanly stop the current Qt event loop if running
    app = QtWidgets.QApplication.instance()
    if app is not None:
        app.quit()  # signals all threads and event loops to stop
    
    # Finally exit the Python process
    os._exit(0)  # force immediate exit, avoids hanging Qt threads


def main():
    """Main entry point for WhisperNinja application"""
    # Set up the application
    qt_app = QtWidgets.QApplication(sys.argv)
    # Hide the application from dock and application switcher
    qt_app.setQuitOnLastWindowClosed(False)
    # On macOS, try to hide from application switcher
    if platform.system() == "Darwin":
        try:
            # Try to set the application as a background agent
            app = NSApplication.sharedApplication()
            app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except ImportError:
            # If AppKit is not available, try alternative approach
            pass

    # Start model load in background immediately (import torch/nemo in thread, not main thread)
    recorder_holder = [None]
    def _start_model_load():
        from whisperninja.src.audio.audio_recorder import AudioRecorder
        r = AudioRecorder(gain=15.0)
        recorder_holder[0] = r
        r.start_background_model_load()
    threading.Thread(target=_start_model_load, daemon=True).start()

    license_manager = LicenseManager.instance()

    if not license_manager.is_installation_complete():
        wizard = RequestPermissionsDialog(license_manager)
        result = wizard.exec()
        if result != QtWidgets.QDialog.DialogCode.Accepted:
            return
        if wizard.requires_restart():
            restart_application()
            return

    pill = AudioWindow()
    settings_manager = SettingsManager()
    settings_window = SettingsWindow(settings_manager)

    # Lazy import MenuBar so main thread never imports audio_recorder (torch/nemo) = no 7s delay
    from whisperninja.src.ui.menu_bar import MenuBar
    MenuBar(qt_app, pill, settings_window, settings_manager, recorder_holder=recorder_holder).run()


if __name__ == "__main__":
    _maybe_handle_permission_helper()
    main()
