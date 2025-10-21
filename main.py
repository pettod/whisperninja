import pyaudio
import wave
import threading
import numpy as np
from datetime import datetime
from pynput import keyboard
from pywhispercpp.model import Model


class AudioRecorder:
    def __init__(self, gain=3.0, model_path="ggml-large-v3-turbo-q5_0.bin"):
        self.is_recording = False
        self.frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.gain = gain
        self.model_path = model_path
        self.whisper_model = None
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        
        # Load Whisper model
        self.whisper_model = Model(model_path)
        
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
            return None
            
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
        return filename
    
    def transcribe(self, audio_file):
        """Transcribe audio file to text"""
        print(f"\n🎯 Transcribing {audio_file}...")
        segments = self.whisper_model.transcribe(audio_file)
        
        # Collect all text from segments
        transcription = ""
        for segment in segments:
            transcription += segment.text + " "
        transcription = transcription.strip()
        
        print("📝 TRANSCRIPTION:")
        print(transcription)
        
        return transcription
    
    def toggle_recording(self):
        """Toggle recording on/off"""
        if self.is_recording:
            filename = self.stop_recording()
            if filename and self.whisper_model:
                self.transcribe(filename)
        else:
            self.start_recording()
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()


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
