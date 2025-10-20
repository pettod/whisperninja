import pyaudio
import wave
import threading
import numpy as np
from datetime import datetime
from pynput import keyboard

class AudioRecorder:
    def __init__(self, gain=3.0):
        self.is_recording = False
        self.frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.gain = gain  # Amplification factor (2.0 = 2x volume, 3.0 = 3x volume)
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        
    def start_recording(self):
        """Start recording audio from microphone"""
        self.is_recording = True
        self.frames = []
        
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        print("🎤 Recording started... Press SPACE again to stop.")
        
        # Record in a separate thread
        def record():
            while self.is_recording:
                data = self.stream.read(self.chunk)
                self.frames.append(data)
        
        self.record_thread = threading.Thread(target=record)
        self.record_thread.start()
    
    def stop_recording(self):
        """Stop recording and save to file"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.record_thread.join()
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
        
        # Amplify the audio
        audio_data = b''.join(self.frames)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Apply gain (amplification) and prevent clipping
        amplified = audio_array.astype(np.float32) * self.gain
        amplified = np.clip(amplified, -32768, 32767)  # Prevent clipping
        amplified = amplified.astype(np.int16)
        
        # Save the amplified recording
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(amplified.tobytes())
        wf.close()
        
        print(f"✅ Recording saved as: {filename} (gain: {self.gain}x)")
    
    def toggle_recording(self):
        """Toggle recording on/off"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()


def main():
    # You can adjust the gain here (default: 3.0)
    # Higher values = louder recording
    # Recommended range: 1.5 - 5.0
    recorder = AudioRecorder(gain=15.0)
    
    print("=" * 50)
    print("🎙️  Microphone Recorder")
    print("=" * 50)
    print(f"\n📊 Volume Gain: {recorder.gain}x")
    print("\nPress SPACE to start/stop recording")
    print("Press ESC to quit")
    print("\nTip: Edit main.py to adjust gain if too quiet/loud\n")
    
    def on_press(key):
        try:
            if key == keyboard.Key.space:
                recorder.toggle_recording()
            elif key == keyboard.Key.esc:
                print("\n👋 Exiting...")
                if recorder.is_recording:
                    recorder.stop_recording()
                recorder.cleanup()
                return False  # Stop listener
        except Exception as e:
            print(f"Error: {e}")
    
    # Start keyboard listener
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
