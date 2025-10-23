import numpy as np
import pyaudio
import threading
import wave
import tempfile
import os
import pygame
import subprocess
from datetime import datetime
from pywhispercpp.model import Model
from utils import insert_text


class AudioRecorder:
    def __init__(self, gain=3.0, model_path="ggml-large-v3-turbo-q5_0.bin", save_recordings=False):
        self.is_recording = False
        self.frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.gain = gain
        self.model_path = model_path
        self.whisper_model = None
        self.save_recordings = save_recordings
        self.temp_file = None  # Track temporary file for cleanup
        self.original_volume = None  # Store original volume level
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        
        # Load Whisper model
        self.whisper_model = Model(model_path)

        # Load sound files
        pygame.mixer.init()
        self.recstart_sound = pygame.mixer.Sound("recstart.mp3")
        self.recstop_sound = pygame.mixer.Sound("recstop.mp3")
    
    def get_system_volume(self):
        """Get current system volume level (0-100)"""
        try:
            result = subprocess.run(["osascript", "-e", "output volume of (get volume settings)"], capture_output=True, text=True, check=True)
            return int(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return None
    
    def set_system_volume(self, volume):
        """Set system volume level (0-100)"""
        try:
            subprocess.run([
                "osascript", "-e", 
                f"set volume output volume {volume}"
            ], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def mute_system_audio(self):
        """Mute system audio and store original volume"""
        if self.original_volume is None:
            self.original_volume = self.get_system_volume()
            if self.original_volume is not None:
                self.set_system_volume(0)
                print("🔇 System audio muted")
            else:
                print("⚠️  Could not get current volume level")
    
    def unmute_system_audio(self):
        """Restore original system volume"""
        if self.original_volume is not None:
            self.set_system_volume(self.original_volume)
            print(f"🔊 System audio restored to {self.original_volume}%")
            self.original_volume = None
        else:
            print("⚠️  No original volume level to restore")
    
    def list_microphones(self):
        """List all available audio input devices"""
        print("\n🎤 Available Microphones:")
        print("-" * 60)
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"  [{i}] {device_info.get('name')}")
                print(f"      Channels: {device_info.get('maxInputChannels')}")
                print(f"      Sample Rate: {int(device_info.get('defaultSampleRate'))} Hz")
        print("-" * 60)
        
    def start_recording(self):
        """Start recording audio from microphone"""
        self.is_recording = True
        self.frames = []
        
        # Mute system audio before starting recording
        self.mute_system_audio()
        
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        print("🎤 Recording started... Press hotkey again to stop.")
        
        # Record in a separate thread
        def record():
            while self.is_recording:
                data = self.stream.read(self.chunk)
                self.frames.append(data)
        
        self.record_thread = threading.Thread(target=record)
        self.record_thread.start()
    
    def stop_recording(self):
        """Stop recording and save to file or temp file based on save_recordings setting"""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        self.record_thread.join()
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        # Determine filename based on save_recordings setting
        if not self.save_recordings:
            # Create a temporary file
            fd, filename = tempfile.mkstemp(suffix='.wav')
            os.close(fd)  # Close the file descriptor, we'll use wave.open
            self.temp_file = filename  # Track for later cleanup
        else:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
            self.temp_file = None  # Not a temp file
        
        # Amplify the audio
        audio_data = b''.join(self.frames)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate duration
        duration_seconds = len(audio_array) / self.rate
        
        # Pad audio if shorter than 1.5 seconds (Whisper requirement + buffer)
        min_duration = 1.1  # seconds (Whisper needs at least 1.0s, we add buffer)
        if duration_seconds < min_duration:
            samples_needed = int(self.rate * min_duration) - len(audio_array)
            padding = np.zeros(samples_needed, dtype=np.int16)
            audio_array = np.concatenate([audio_array, padding])
            print(f"⚠️  Recording too short ({duration_seconds:.2f}s), padded to {min_duration}s")
            duration_seconds = min_duration  # Update duration after padding
        
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
        
        if self.temp_file:
            print(f"✅ Recording processed (gain: {self.gain}x, duration: {duration_seconds:.2f}s)")
        else:
            print(f"✅ Recording saved as: {filename} (gain: {self.gain}x, duration: {duration_seconds:.2f}s)")
        
        return filename
    
    def cancel_recording(self):
        """Cancel recording without saving or transcribing"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        if hasattr(self, 'record_thread'):
            self.record_thread.join()
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        # Clear the frames without saving
        self.frames = []
        print("🚫 Recording cancelled - no audio saved or transcribed")
    
    def transcribe(self, audio_file, language="auto", space_at_end=False):
        """Transcribe audio file to text and clean up temp file if needed"""
        print(f"\n🎯 Transcribing {audio_file}...")
        segments = self.whisper_model.transcribe(audio_file, language=language)
        
        # Collect all text from segments
        transcription = ""
        for segment in segments:
            transcription += segment.text + " "
        transcription = transcription.strip()
        
        # Transcribe text to clipboard
        if space_at_end:
            insert_text(transcription + " ")
        else:
            insert_text(transcription)
        print(transcription)
        
        # Clean up temporary file if it exists
        if self.temp_file and os.path.exists(self.temp_file):
            os.remove(self.temp_file)
            print(f"🗑️  Temporary file cleaned up")
            self.temp_file = None
        
        return transcription
    
    def toggle_recording(self):
        """Toggle recording on/off"""
        if self.is_recording:
            filename = self.stop_recording()
            self.recstop_sound.play()
            if filename and self.whisper_model:
                self.transcribe(filename, "auto")
        else:
            self.recstart_sound.play()
            self.start_recording()
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        # Ensure system audio is unmuted on cleanup
        self.unmute_system_audio()
