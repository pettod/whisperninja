from pynput import keyboard
from audio_recorder import AudioRecorder


def main():
    recorder = AudioRecorder(gain=15.0)
    
    print(f"\n📊 Volume Gain: {recorder.gain}x")
    print("\nPress SPACE to start/stop recording")
    print("Press ESC to quit")
    
    def on_press(key):
        try:
            if key == keyboard.Key.space:
                recorder.toggle_recording()
            elif key == keyboard.Key.esc:
                if recorder.is_recording:
                    filename = recorder.stop_recording()
                    if filename and recorder.whisper_model:
                        recorder.transcribe(filename)
                recorder.cleanup()
                return False  # Stop listener
        except Exception as e:
            print(f"Error: {e}")
    
    # Start keyboard listener
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
