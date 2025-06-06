from typing import Dict, Any, Optional, Union, BinaryIO
import os
import io
import tempfile
import asyncio
from enum import Enum

from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger("services.telephony.text_to_speech")
settings = get_settings()

class VoiceGender(str, Enum):
    """Enumeration of voice genders"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

class TTSService:
    """
    Text-to-Speech service for generating spoken audio from text.
    Supports multiple providers based on configuration.
    """
    
    def __init__(self):
        """Initialize TTS service based on configured provider"""
        self.provider = settings.TTS_PROVIDER.lower()
        
        if self.provider == "google":
            self._initialize_google()
        elif self.provider == "elevenlabs":
            self._initialize_elevenlabs()
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")
    
    def _initialize_google(self):
        """Initialize Google Text-to-Speech client"""
        from google.cloud import texttospeech
        
        self.client = texttospeech.TextToSpeechClient()
        
        # Map of voice types to Google voice names
        self.voice_map = {
            "neutral_female": "en-US-Neural2-F",
            "neutral_male": "en-US-Neural2-D",
            "professional_female": "en-US-Neural2-E",
            "professional_male": "en-US-Neural2-J",
            "friendly_female": "en-US-Wavenet-F",
            "friendly_male": "en-US-Wavenet-I"
        }
    
    def _initialize_elevenlabs(self):
        """Initialize ElevenLabs client"""
        import elevenlabs
        
        elevenlabs.set_api_key(settings.ELEVENLABS_API_KEY)
        self.client = elevenlabs
        
        # Map of voice types to ElevenLabs voice IDs
        # These are example IDs - in a real implementation, use actual ElevenLabs voice IDs
        self.voice_map = {
            "neutral_female": "21m00Tcm4TlvDq8ikWAM",
            "neutral_male": "AZnzlk1XvdvUeBnXmlld",
            "professional_female": "EXAVITQu4vr4xnSDxMaL",
            "professional_male": "VR6AewLTigWG4xSOukaG",
            "friendly_female": "D38z5RcWu1voky8WS1ja",
            "friendly_male": "MF3mGyEYCl7XYWbV9V6O"
        }
    
    async def synthesize_speech(
        self, 
        text: str,
        voice_type: str = "neutral_female",
        language_code: str = "en-US",
        output_format: str = "mp3",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0
    ) -> Dict[str, Any]:
        """
        Convert text to speech
        
        Args:
            text: Text to convert to speech
            voice_type: Type of voice to use (e.g., neutral_female, professional_male)
            language_code: Language code for speech
            output_format: Audio format (mp3, wav, etc.)
            speaking_rate: Speaking rate (0.25 to 4.0)
            pitch: Voice pitch (-20.0 to 20.0)
            volume_gain_db: Volume gain (-96.0 to 16.0)
            
        Returns:
            Dict: Synthesis results including audio data
        """
        try:
            # Route to appropriate provider
            if self.provider == "google":
                return await self._synthesize_google(
                    text, 
                    voice_type,
                    language_code,
                    output_format,
                    speaking_rate,
                    pitch,
                    volume_gain_db
                )
            elif self.provider == "elevenlabs":
                return await self._synthesize_elevenlabs(
                    text, 
                    voice_type,
                    language_code,
                    output_format,
                    speaking_rate,
                    pitch
                )
                
        except Exception as e:
            logger.error(f"Error synthesizing speech: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "audio_data": None
            }
    
    async def _synthesize_google(
        self,
        text: str,
        voice_type: str,
        language_code: str,
        output_format: str,
        speaking_rate: float,
        pitch: float,
        volume_gain_db: float
    ) -> Dict[str, Any]:
        """Synthesize speech using Google Text-to-Speech"""
        try:
            from google.cloud import texttospeech
            
            # Get voice name from map or use voice_type as fallback
            voice_name = self.voice_map.get(voice_type, voice_type)
            
            # Determine voice gender
            gender = texttospeech.SsmlVoiceGender.NEUTRAL
            if "female" in voice_type or voice_name.endswith(("F", "A", "C", "E")):
                gender = texttospeech.SsmlVoiceGender.FEMALE
            elif "male" in voice_type or voice_name.endswith(("M", "B", "D")):
                gender = texttospeech.SsmlVoiceGender.MALE
            
            # Determine audio encoding
            audio_encoding = texttospeech.AudioEncoding.MP3
            if output_format.lower() == "wav":
                audio_encoding = texttospeech.AudioEncoding.LINEAR16
            elif output_format.lower() == "ogg":
                audio_encoding = texttospeech.AudioEncoding.OGG_OPUS
            
            # Create synthesis input
            input_text = texttospeech.SynthesisInput(text=text)
            
            # Create voice config
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
                ssml_gender=gender
            )
            
            # Create audio config
            audio_config = texttospeech.AudioConfig(
                audio_encoding=audio_encoding,
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=volume_gain_db
            )
            
            # Perform text-to-speech request
            response = await asyncio.to_thread(
                self.client.synthesize_speech,
                input=input_text,
                voice=voice,
                audio_config=audio_config
            )
            
            return {
                "success": True,
                "audio_data": response.audio_content,
                "format": output_format,
                "voice_type": voice_type,
                "provider": "google"
            }
            
        except Exception as e:
            logger.error(f"Google TTS error: {str(e)}", exc_info=True)
            raise
    
    async def _synthesize_elevenlabs(
        self,
        text: str,
        voice_type: str,
        language_code: str,
        output_format: str,
        speaking_rate: float,
        pitch: float
    ) -> Dict[str, Any]:
        """Synthesize speech using ElevenLabs"""
        try:
            # Get voice ID from map or use voice_type as fallback
            voice_id = self.voice_map.get(voice_type, voice_type)
            
            # Adapt speaking rate to ElevenLabs format (0.25-4.0 to 0.5-2.0)
            stability = 0.5  # Default stability
            similarity_boost = 0.75  # Default similarity boost
            
            # Map speaking_rate to ElevenLabs speaking rate
            eleven_speaking_rate = max(0.5, min(2.0, speaking_rate))
            
            # Generate audio
            audio_data = await asyncio.to_thread(
                self.client.generate,
                text=text,
                voice=voice_id,
                model="eleven_monolingual_v1"
            )
            
            # For ElevenLabs, we might need to convert to the requested format
            # Since ElevenLabs returns MP3 by default
            if output_format.lower() != "mp3":
                # In a real implementation, you'd convert the audio format here
                # For now, we'll just return MP3
                logger.warning(f"ElevenLabs only supports MP3 output, ignoring requested format: {output_format}")
            
            return {
                "success": True,
                "audio_data": audio_data,
                "format": "mp3",  # ElevenLabs always returns MP3
                "voice_type": voice_type,
                "provider": "elevenlabs"
            }
            
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {str(e)}", exc_info=True)
            raise
    
    async def save_audio_to_file(
        self,
        audio_data: bytes,
        file_path: str
    ) -> bool:
        """
        Save audio data to a file
        
        Args:
            audio_data: Audio data as bytes
            file_path: Path to save the audio file
            
        Returns:
            bool: Whether the save was successful
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # Write the file
            with open(file_path, "wb") as f:
                f.write(audio_data)
            
            return True
        except Exception as e:
            logger.error(f"Error saving audio to file: {str(e)}", exc_info=True)
            return False