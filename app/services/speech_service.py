"""Speech-to-text service using Bhashini API"""
import base64
import io
import httpx
from typing import Optional

from ..config import get_settings


class SpeechService:
    """Service for speech-to-text conversion using Bhashini API"""
    
    def __init__(self):
        self._settings = get_settings()
    
    async def transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribe audio bytes to text using Bhashini ASR.
        
        Args:
            audio_bytes: Raw audio bytes (WAV format expected)
            
        Returns:
            Transcribed text or None if failed
        """
        # Encode audio to base64
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        payload = {
            "pipelineTasks": [{
                "taskType": "asr",
                "config": {
                    "language": {"sourceLanguage": "en"},
                    "serviceId": "ai4bharat/whisper-medium-en--gpu--t4",
                    "audioFormat": "wav",
                    "samplingRate": 16000,
                    "preProcessors": ["vad"],
                    "postProcessors": ["itn"]
                }
            }],
            "inputData": {
                "audio": [{"audioContent": audio_b64}]
            }
        }
        
        headers = {
            "Authorization": self._settings.bhashini_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self._settings.bhashini_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                # Extract transcribed text
                text = (
                    result.get("pipelineResponse", [{}])[0]
                    .get("output", [{}])[0]
                    .get("source", "")
                    .strip()
                )
                
                return text if text else None
                
        except httpx.HTTPError as e:
            print(f"Bhashini API error: {e}")
            return None
        except Exception as e:
            print(f"Transcription error: {e}")
            return None
    
    async def text_to_speech(self, text: str, gender: str = "female") -> Optional[bytes]:
        """
        Convert text to speech using Bhashini TTS.
        
        Args:
            text: Text to convert to speech
            gender: Voice gender ("male" or "female")
            
        Returns:
            Audio bytes or None if failed
        """
        payload = {
            "pipelineTasks": [{
                "taskType": "tts",
                "config": {
                    "language": {"sourceLanguage": "en"},
                    "serviceId": "ai4bharat/indic-tts-coqui-misc-gpu--t4",
                    "gender": gender
                }
            }],
            "inputData": {
                "input": [{"source": text}]
            }
        }
        
        headers = {
            "Authorization": self._settings.bhashini_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self._settings.bhashini_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                # Extract audio content
                audio_b64 = (
                    result.get("pipelineResponse", [{}])[0]
                    .get("audio", [{}])[0]
                    .get("audioContent", "")
                )
                
                if audio_b64:
                    return base64.b64decode(audio_b64)
                return None
                
        except Exception as e:
            print(f"TTS error: {e}")
            return None
    
    async def check_health(self) -> bool:
        """Check if Bhashini API is accessible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Just check if we can reach the endpoint
                response = await client.options(self._settings.bhashini_url)
                return response.status_code < 500
        except Exception:
            return False
