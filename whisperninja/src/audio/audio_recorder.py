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
import torch
import nemo.collections.asr as nemo_asr
from whisperninja.src.utils.utils import insert_text, resource_path
from whisperninja.src.license.license_manager import LicenseManager

# Parakeet (NeMo) transcribe options: use_lhotse=False avoids Lhotse dataloader warning
TRANSCRIBE_OPTS = {"use_lhotse": False, "num_workers": 0}
# Lock for NeMo transcribe (not fully thread-safe)
_transcribe_lock = threading.Lock()

# Parakeet model name (English ASR)
PARAKEET_MODEL = "nvidia/parakeet-tdt-0.6b-v3"


class AudioRecorder:
    def __init__(self, gain=3.0, save_recordings=False):
        self.is_recording = False
        self.frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.gain = gain
        self._asr_model = None  # NeMo Parakeet model (loaded at startup in background)
        self._load_lock = threading.Lock()  # One thread loads; others wait
        self._progress_callback = None  # Called from loader thread; UI should invoke on main thread
        self.save_recordings = save_recordings
        self.current_language = None
        self.temp_file = None  # Track temporary file for cleanup
        self.original_volume = None  # Store original volume level
        
        # Audio settings (16 kHz for Parakeet)
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        
        # Load sound files
        pygame.mixer.init()
        self.recstart_sound = pygame.mixer.Sound(resource_path("whisperninja/assets/sounds/recstart.mp3"))
        self.recstop_sound = pygame.mixer.Sound(resource_path("whisperninja/assets/sounds/recstop.mp3"))

        # Model load thread is started by start_background_model_load() after the UI sets the
        # progress callback, so the progress bar actually receives updates.
    
    def start_background_model_load(self):
        """Start loading the ASR model on a background thread. Call after set_model_load_progress_callback."""
        threading.Thread(target=self._load_model, daemon=True).start()

    def set_model_load_progress_callback(self, callback):
        """Set a callback (progress: float 0..1, status: str) for UI updates. Call from main thread."""
        self._progress_callback = callback

    def reload_model_if_needed(self, language):
        """Update language for UI compatibility; Parakeet is single-model, no reload."""
        self.current_language = language

    def _report_progress(self, progress: float, status: str):
        if self._progress_callback:
            try:
                self._progress_callback(progress, status)
            except Exception:
                pass

    def _load_model(self, language=None):
        """Load the NeMo Parakeet ASR model (once). Thread-safe: one thread loads, others wait."""
        if self._asr_model is not None:
            return self._asr_model
        with self._load_lock:
            if self._asr_model is not None:
                return self._asr_model
            self.current_language = language or self.current_language
            # Only show progress bar when actually downloading; when loading from cache, don't report
            download_occurred = [False]  # list so inner function can mutate
            print("⏳ Loading Parakeet ASR model in background...")
            print(f"📦 Model: {PARAKEET_MODEL}")
            device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

            # Use tqdm's progress: n = bytes actually downloaded, total = total bytes (disk/received, not reserved)
            last_reported = [0.0]
            report = self._report_progress

            def make_patched_update(original_update):
                def _patched_update(self, n=1):
                    out = original_update(self, n)
                    if not (report and getattr(self, "total", None) and self.total > 0):
                        return out
                    if not download_occurred[0]:
                        download_occurred[0] = True
                        report(0.0, "Preparing to download…")
                    # Progress from the bar: bytes downloaded (n) / total bytes – actual size on disk
                    bytes_downloaded = self.n
                    total_bytes = self.total
                    pct = min(1.0, bytes_downloaded / total_bytes)
                    # Monotonic: never report less than last time
                    pct = max(pct, last_reported[0])
                    last_reported[0] = pct
                    report(pct, "Downloading…")
                    return out
                return _patched_update

            try:
                import tqdm.auto
                base_tqdm = tqdm.auto.tqdm
                _original_update = base_tqdm.update
                base_tqdm.update = make_patched_update(_original_update)
                try:
                    self._asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name=PARAKEET_MODEL, map_location=device, strict=False)
                finally:
                    base_tqdm.update = _original_update
            except Exception:
                self._asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name=PARAKEET_MODEL, map_location=device, strict=False)

            # Only report "Preparing…" / 0.85 and show progress when we actually downloaded; else skip to 1.0
            if download_occurred[0]:
                self._report_progress(0.85, "Preparing…")
            # Required for RNN-T: _transcribe_on_end() calls encoder/decoder/joint.unfreeze(partial=True)
            for name in ("encoder", "decoder", "joint"):
                if hasattr(self._asr_model, name):
                    getattr(self._asr_model, name).freeze()
            self._asr_model.freeze()
            self._report_progress(1.0, "Ready")
            print("✅ Parakeet ASR model ready")
        return self._asr_model
    
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
        
    def _warmup(self):
        """Run ASR warmup on a short file using the transcribe lock (like a.py). Call on a background thread."""
        warmup_path = resource_path("whisperninja/assets/sounds/warmup.wav")
        if not os.path.exists(warmup_path):
            return
        model = self._load_model()
        with _transcribe_lock:
            with torch.inference_mode():
                model.transcribe([warmup_path], **TRANSCRIBE_OPTS)

    def start_recording(self, microphone_name="Default"):
        """Start recording audio from microphone"""
        # Validate microphone (triggers fallback callback if needed)
        self.validate_microphone(microphone_name)
        
        # Run warmup on another thread (uses lock like a.py) so first real transcribe is faster
        threading.Thread(target=self._warmup, daemon=True).start()

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
        
        # Pad audio if shorter than 1.1 seconds (ASR needs minimum duration)
        min_duration = 1.1  # seconds
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
        model = self._load_model(language=language)
        with _transcribe_lock:
            with torch.inference_mode():
                results = model.transcribe([audio_file], **TRANSCRIBE_OPTS)
        # NeMo returns list of Hypothesis or str; single file -> one element
        if not results:
            transcription = ""
        else:
            first = results[0]
            transcription = (getattr(first, "text", None) or first) if not isinstance(first, str) else first
            transcription = (transcription or "").strip()
        end_time = time.time()
        print(f"🎯 Transcribing time: {end_time - start_time:.2f} seconds")

        # Check license status and prepend trial message if needed
        license_manager = LicenseManager.instance()
        
        if license_manager.should_show_trial_message():
            trial_message = "Your WhisperNinja trial has expired. Please buy a license from https://whisperninja.app\n\n"
            transcription = trial_message + transcription

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
