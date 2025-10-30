import numpy as np
import pyaudio
import threading
import wave
import tempfile
import os
import pygame
import subprocess
import time
from datetime import datetime
from pywhispercpp.model import Model
from whisperninja.utils import insert_text, resource_path


class AudioRecorder:
    def __init__(self, gain=3.0, model_path="whisperninja/assets/models/ggml-large-v3-turbo-q5_0.bin", save_recordings=False):
        self.is_recording = False
        self.frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.gain = gain
        self.whisper_model = None
        self.model_path = resource_path(model_path)
        self.save_recordings = save_recordings
        self.temp_file = None  # Track temporary file for cleanup
        self.original_volume = None  # Store original volume level
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        
        # Load sound files
        pygame.mixer.init()
        self.recstart_sound = pygame.mixer.Sound(resource_path("whisperninja/assets/sounds/recstart.mp3"))
        self.recstop_sound = pygame.mixer.Sound(resource_path("whisperninja/assets/sounds/recstop.mp3"))
    
    def _load_model(self):
        """Lazy load the Whisper model - only load when first needed"""
        if self.whisper_model is None:
            print("⏳ Loading Whisper model... (this happens once)")
            self.whisper_model = Model(self.model_path)
        return self.whisper_model
    
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
    
    def get_available_microphones(self):
        """Get list of available microphone names"""
        microphones = []
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                microphones.append(device_info.get('name'))
        return microphones
    
    def validate_microphone(self, microphone_name):
        """Validate if microphone exists and return the correct microphone to use"""
        available_mics = self.get_available_microphones()
        
        if microphone_name == "Default" or microphone_name in available_mics:
            return microphone_name
        else:
            print(f"⚠️  Microphone '{microphone_name}' not found, using default")
            # Call the fallback callback if it exists
            if hasattr(self, 'microphone_fallback_callback') and self.microphone_fallback_callback:
                self.microphone_fallback_callback("Default")
            return "Default"
    
    def set_microphone_fallback_callback(self, callback):
        """Set callback to be called when microphone fallback occurs"""
        self.microphone_fallback_callback = callback
        
    def start_recording(self, microphone_name="Default"):
        """Start recording audio from microphone"""
        # Validate microphone (triggers fallback callback if needed)
        self.validate_microphone(microphone_name)
        
        self.is_recording = True
        self.frames = []
        
        # Start audio stream first for immediate response
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
        
        # Mute system audio after stream is started (non-blocking)
        threading.Thread(target=self.mute_system_audio, daemon=True).start()
    
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
        
        # Optimized audio processing
        audio_data = b''.join(self.frames)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate duration
        duration_seconds = len(audio_array) / self.rate
        
        # Pad audio if shorter than 1.1 seconds (optimized threshold)
        min_duration = 1.1  # seconds (Whisper needs at least 1.0s, we add buffer)
        if duration_seconds < min_duration:
            samples_needed = int(self.rate * min_duration) - len(audio_array)
            padding = np.zeros(samples_needed, dtype=np.int16)
            audio_array = np.concatenate([audio_array, padding])
            print(f"⚠️  Recording too short ({duration_seconds:.2f}s), padded to {min_duration}s")
            duration_seconds = min_duration  # Update duration after padding
        
        # Optimized gain application - use vectorized operations
        if self.gain != 1.0:
            # Convert to float32 for processing, apply gain, clip, convert back
            amplified = np.clip(audio_array.astype(np.float32) * self.gain, -32768, 32767).astype(np.int16)
        else:
            amplified = audio_array
        
        # Save the recording with optimized I/O
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(amplified.tobytes())
        
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
    
    def transcribe(self, audio_file, language=None, space_at_end=False):
        """Transcribe audio file to text and clean up temp file if needed"""
        start_time = time.time()

        print(f"\n🎯 Transcribing {audio_file}...")
        # Use optimized transcription parameters for maximum speed
        model = self._load_model()  # Lazy load model if not already loaded
        segments = model.transcribe(audio_file, language=language)
        
        # Optimized text collection - use join instead of string concatenation
        transcription = " ".join(segment.text for segment in segments).strip()
        end_time = time.time()
        print(f"🎯 Transcribing time: {end_time - start_time:.2f} seconds")

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
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        # Ensure system audio is unmuted on cleanup
        self.unmute_system_audio()
