import sys
import platform
from PyQt6 import QtWidgets
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
from whisperninja.menu_bar import MenuBar
from whisperninja.audio_window import AudioWindow
from whisperninja.settings_manager import SettingsManager
from whisperninja.settings_window import SettingsWindow
from whisperninja.system_permission_tests import test_system_permissions

def main():
    """Main entry point for WhisperNinja application"""
    test_system_permissions()
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
    
    pill = AudioWindow()
    settings_manager = SettingsManager()
    settings_window = SettingsWindow(settings_manager)
    MenuBar(qt_app, pill, settings_window, settings_manager).run()


if __name__ == "__main__":
    main()
