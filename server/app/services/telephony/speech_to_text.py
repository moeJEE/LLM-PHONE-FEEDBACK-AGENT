from typing import Dict, Any, Optional, Union, BinaryIO
import os
import io
import asyncio
from urllib.parse import urlparse
import httpx

from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger("services.telephony.speech_to_text")
settings = get_settings()

class STTService:
    """
    Speech-to-Text service for transcribing audio from phone calls.
    Supports multiple providers based on configuration.
    """
    
    def __init__(self):
        """Initialize STT service based on configured provider"""
        self.provider = settings.STT_PROVIDER.lower()
        
        if self.provider == "deepgram":
            self._initialize_deepgram()
        elif self.provider == "google":
            self._initialize_google()
        else:
            raise ValueError(f"Unsupported STT provider: {self.provider}")
    
    def _initialize_deepgram(self):
        """Initialize Deepgram STT client"""
        from deepgram import Deepgram
        
        self.client = Deepgram(settings.DEEPGRAM_API_KEY)
    
    def _initialize_google(self):
        """Initialize Google Speech-to-Text client"""
        from google.cloud import speech
        
        self.client = speech.SpeechClient()
    
    async def transcribe_audio(
        self, 
        audio_source: Union[str, bytes, BinaryIO],
        language_code: str = "en-US",
        audio_format: Optional[str] = None,
        sample_rate: int = 8000,
        channels: int = 1
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text
        
        Args:
            audio_source: Audio file path, URL, or bytes
            language_code: Language code for transcription
            audio_format: Format of audio (mp3, wav, etc.)
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            
        Returns:
            Dict: Transcription results
        """
        try:
            # Determine whether audio_source is a file path, URL, or bytes
            if isinstance(audio_source, str):
                if audio_source.startswith(("http://", "https://")):
                    # It's a URL, download the content
                    async with httpx.AsyncClient() as client:
                        response = await client.get(audio_source)
                        response.raise_for_status()
                        audio_data = response.content
                        
                        # Try to determine format from URL if not provided
                        if not audio_format:
                            path = urlparse(audio_source).path
                            ext = os.path.splitext(path)[1].lower()
                            if ext:
                                audio_format = ext[1:]  # Remove the dot
                else:
                    # It's a file path
                    with open(audio_source, "rb") as f:
                        audio_data = f.read()
                        
                        # Try to determine format from file extension if not provided
                        if not audio_format:
                            ext = os.path.splitext(audio_source)[1].lower()
                            if ext:
                                audio_format = ext[1:]  # Remove the dot
            elif isinstance(audio_source, (bytes, bytearray)):
                # It's already bytes
                audio_data = audio_source
            else:
                # Assume it's a file-like object
                audio_data = audio_source.read()
            
            # Route to appropriate provider
            if self.provider == "deepgram":
                return await self._transcribe_deepgram(
                    audio_data, 
                    language_code,
                    audio_format,
                    sample_rate,
                    channels
                )
            elif self.provider == "google":
                return await self._transcribe_google(
                    audio_data, 
                    language_code,
                    audio_format,
                    sample_rate,
                    channels
                )
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "transcription": "",
                "confidence": 0.0
            }
    
    async def _transcribe_deepgram(
        self,
        audio_data: bytes,
        language_code: str,
        audio_format: Optional[str],
        sample_rate: int,
        channels: int
    ) -> Dict[str, Any]:
        """Transcribe using Deepgram"""
        try:
            # Set up options
            options = {
                "punctuate": True,
                "language": language_code[:2],  # Deepgram uses 2-letter language code
                "model": "general",
                "diarize": channels > 1,
                "utterances": True
            }
            
            if sample_rate:
                options["sample_rate"] = sample_rate
            
            # Determine mimetype
            mimetype = None
            if audio_format:
                if audio_format.lower() in ["mp3", "mpeg"]:
                    mimetype = "audio/mpeg"
                elif audio_format.lower() in ["wav", "wave"]:
                    mimetype = "audio/wav"
                elif audio_format.lower() in ["ogg", "opus"]:
                    mimetype = "audio/ogg"
                elif audio_format.lower() in ["flac"]:
                    mimetype = "audio/flac"
                else:
                    mimetype = f"audio/{audio_format.lower()}"
            
            # Send request to Deepgram
            response = await self.client.transcription.prerecorded(
                {"buffer": audio_data, "mimetype": mimetype},
                options
            )
            
            # Extract results
            results = response["results"]
            channels_result = results["channels"]
            
            if not channels_result:
                return {
                    "success": False,
                    "error": "No transcription results",
                    "transcription": "",
                    "confidence": 0.0
                }
            
            # Get the first channel's transcription
            alternatives = channels_result[0]["alternatives"]
            if not alternatives:
                return {
                    "success": False,
                    "error": "No transcription alternatives",
                    "transcription": "",
                    "confidence": 0.0
                }
            
            transcript = alternatives[0]["transcript"]
            confidence = alternatives[0].get("confidence", 0.0)
            
            return {
                "success": True,
                "transcription": transcript,
                "confidence": confidence,
                "language": language_code,
                "provider": "deepgram"
            }
            
        except Exception as e:
            logger.error(f"Deepgram transcription error: {str(e)}", exc_info=True)
            raise
    
    async def _transcribe_google(
        self,
        audio_data: bytes,
        language_code: str,
        audio_format: Optional[str],
        sample_rate: int,
        channels: int
    ) -> Dict[str, Any]:
        """Transcribe using Google Speech-to-Text"""
        try:
            from google.cloud import speech
            
            # Create proper encoding type based on format
            encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16  # Default
            if audio_format:
                format_lower = audio_format.lower()
                if format_lower in ["mp3", "mpeg"]:
                    encoding = speech.RecognitionConfig.AudioEncoding.MP3
                elif format_lower in ["flac"]:
                    encoding = speech.RecognitionConfig.AudioEncoding.FLAC
                elif format_lower in ["ogg", "opus"]:
                    encoding = speech.RecognitionConfig.AudioEncoding.OGG_OPUS
                elif format_lower in ["wav", "wave"] and sample_rate == 8000:
                    encoding = speech.RecognitionConfig.AudioEncoding.MULAW
            
            # Create recognition config
            config = speech.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=sample_rate,
                language_code=language_code,
                enable_automatic_punctuation=True,
                audio_channel_count=channels
            )
            
            # Create audio object
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Make request
            operation = self.client.recognize(config=config, audio=audio)
            
            # Process results
            results = operation.results
            
            if not results:
                return {
                    "success": False,
                    "error": "No transcription results",
                    "transcription": "",
                    "confidence": 0.0
                }
            
            # Get the first result
            result = results[0]
            if not result.alternatives:
                return {
                    "success": False,
                    "error": "No transcription alternatives",
                    "transcription": "",
                    "confidence": 0.0
                }
            
            alternative = result.alternatives[0]
            transcript = alternative.transcript
            confidence = alternative.confidence
            
            return {
                "success": True,
                "transcription": transcript,
                "confidence": confidence,
                "language": language_code,
                "provider": "google"
            }
            
        except Exception as e:
            logger.error(f"Google transcription error: {str(e)}", exc_info=True)
            raise