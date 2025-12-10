import speech_recognition as sr
import tempfile
import os
import numpy as np
from typing import Optional, Tuple
import logging
from transformers import pipeline
import torch
import wave
import io
import requests

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.asr_pipeline = None
        self._load_models()
    
    def _load_models(self):
        """Load better models for Urdu/English speech recognition"""
        try:
            print("🎤 Loading improved HuggingFace model for voice recognition...")
            
            # Use a better model for multilingual support
            self.asr_pipeline = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-small",  # Better accuracy than wav2vec2
                device=-1  # Use CPU
            )
            print("✅ Improved Whisper model loaded successfully!")
            
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            print("🔧 Using Google Speech Recognition as fallback")
            self.asr_pipeline = None
    
    def transcribe_audio_whisper(self, audio_file_path: str) -> Tuple[str, bool]:
        """Transcribe audio using Whisper model - FIXED VERSION"""
        try:
            if self.asr_pipeline is None:
                return "", False

            # Read audio file
            import soundfile as sf
            audio_data, sample_rate = sf.read(audio_file_path)

            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            # Resample to 16kHz if necessary (Whisper expects 16kHz)
            if sample_rate != 16000:
                import librosa
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
                print(f"🔄 Resampled from {sample_rate}Hz to 16000Hz")

            # Normalize
            audio_data = audio_data.astype(np.float32)
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data))

            # Transcribe using correct API - FIXED: Remove sampling_rate parameter
            # Whisper model in transformers pipeline doesn't need sampling_rate parameter
            result = self.asr_pipeline(audio_data)

            transcription = result["text"].strip()

            if transcription:
                print(f"🎤 Whisper Transcription: {transcription}")
                return transcription, True

            return "", False

        except Exception as e:
            print(f"❌ Whisper transcription error: {e}")
            import traceback
            traceback.print_exc()
            return "", False
    
    def transcribe_audio_whisper_direct(self, audio_file_path: str) -> Tuple[str, bool]:
        """Alternative method using direct Whisper model (if pipeline fails)"""
        try:
            # Try importing whisper library directly
            import whisper
            
            # Load the model
            model = whisper.load_model("small")
            
            # Transcribe
            result = model.transcribe(audio_file_path, language="en")
            
            transcription = result["text"].strip()
            
            if transcription:
                print(f"🎤 Whisper Direct Transcription: {transcription}")
                return transcription, True
                
            return "", False
            
        except ImportError:
            print("⚠️ OpenAI whisper library not installed. Install with: pip install openai-whisper")
            return "", False
        except Exception as e:
            print(f"❌ Whisper direct transcription error: {e}")
            return "", False
    
    def transcribe_audio_google(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[str, bool]:
        """Transcribe audio using Google Speech Recognition"""
        try:
            # Convert to proper format
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            audio_bytes = audio_data.tobytes()
            audio_data_sr = sr.AudioData(audio_bytes, sample_rate, 2)
            
            # Try multiple language combinations
            languages = ["en-US", "en-IN", "ur-PK"]
            
            for lang in languages:
                try:
                    text = self.recognizer.recognize_google(audio_data_sr, language=lang)
                    if text and len(text.strip()) > 3:  # Minimum length
                        print(f"🎤 Google Transcription ({lang}): {text}")
                        return text, True
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    print(f"Google API request error for {lang}: {e}")
                    continue
            
            return "", False
            
        except Exception as e:
            print(f"❌ Google transcription error: {e}")
            return "", False
    
    def process_voice_order(self, audio_file_path: str) -> str:
        """Process voice order from audio file with improved error handling"""
        try:
            if not os.path.exists(audio_file_path):
                print(f"❌ Audio file not found: {audio_file_path}")
                return ""
            
            # First try the fixed Whisper method
            transcription, success = self.transcribe_audio_whisper(audio_file_path)
            if success:
                return transcription
            
            # If that fails, try direct Whisper library
            transcription, success = self.transcribe_audio_whisper_direct(audio_file_path)
            if success:
                return transcription
            
            # Finally fallback to Google
            import soundfile as sf
            audio_data, sample_rate = sf.read(audio_file_path)
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            transcription, success = self.transcribe_audio_google(audio_data, sample_rate)
            if success:
                return transcription
            
            print("❌ All transcription methods failed")
            print("💡 Tips for better voice recognition:")
            print("   - Speak clearly in English")
            print("   - Keep recording 3-5 seconds")
            print("   - Reduce background noise")
            print("   - Say numbers clearly (one, two, three)")
            
            return ""
            
        except Exception as e:
            print(f"❌ Error processing voice order: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def supported_languages(self) -> list:
        """Get supported languages"""
        return ["English", "Urdu", "Hindi", "Roman Urdu"]
    
    def get_voice_instructions(self) -> str:
        """Get voice recording instructions"""
        return """
        **🎤 How to Place Voice Order:**
        
        1. Click **Record Button**
        2. Speak your order clearly
        3. Click **Stop Button**
        4. Voice will be automatically processed
        
        **Examples (Speak in English):**
        • "I want 2 tea and 1 samosa"
        • "One zinger burger please"
        • "Two chicken biryani for delivery"
        
        **Tips for Better Recognition:**
        • Speak clearly and slowly
        • Say numbers clearly (one, two, three)
        • Reduce background noise
        • Speak in English for best results
        """
    
    def get_voice_health(self) -> dict:
        """Check voice service health and capabilities"""
        health_info = {
            "service": "VoiceService",
            "status": "active",
            "models_loaded": False,
            "primary_model": None,
            "supported_formats": ["WAV", "MP3", "M4A", "OGG"],
            "supported_languages": self.supported_languages(),
            "fallback_methods": ["Google Speech Recognition"]
        }
        
        if self.asr_pipeline is not None:
            health_info["models_loaded"] = True
            health_info["primary_model"] = "HuggingFace Whisper-small"
        
        # Check if direct whisper is available
        try:
            import whisper
            health_info["direct_whisper"] = True
        except ImportError:
            health_info["direct_whisper"] = False
            
        return health_info

# Global instance
voice_service = VoiceService()