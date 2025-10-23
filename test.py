from pynput import keyboard
from audio_recorder import AudioRecorder


def main():
    recorder = AudioRecorder(gain=15.0)
    
    # List available microphones
    recorder.list_microphones()
    
    print(f"\n📊 Volume Gain: {recorder.gain}x")
    print("\nPress SPACE to start/stop recording")
    print("Press ESC during recording to cancel (no transcription)")
    print("Press ESC when not recording to quit")
    
    def on_press(key):
        try:
            if key == keyboard.Key.space:
                recorder.toggle_recording()
            elif key == keyboard.Key.esc:
                if recorder.is_recording:
                    # Cancel recording without transcribing
                    recorder.cancel_recording()
                    print("Recording cancelled by ESC key")
                else:
                    # Quit when not recording
                    recorder.cleanup()
                    return False  # Stop listener
        except Exception as e:
            print(f"Error: {e}")
    
    # Start keyboard listener
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
