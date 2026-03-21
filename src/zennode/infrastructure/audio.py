import os

import structlog
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from zennode.core.interfaces import ITranscriptionService
from zennode.infrastructure.config import Config

logger = structlog.get_logger(__name__)

class GroqWhisperService(ITranscriptionService):
    def __init__(self) -> None:
        self.client = Groq(api_key=Config.get_groq_api_key())
        self.model = "whisper-large-v3"

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3), reraise=True)
    def transcribe(self, audio_file_path: str) -> str:
        if not os.path.exists(audio_file_path):
            logger.error("audio_file_not_found", path=audio_file_path)
            raise FileNotFoundError(f"Audio file not found at {audio_file_path}")
            
        logger.info("whisper_transcription_started", path=audio_file_path, model=self.model)
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=(os.path.basename(audio_file_path), audio_file.read()),
                    model=self.model,
                )
            logger.info("whisper_transcription_success", text_length=len(transcription.text))
            return transcription.text
        except Exception as e:
            logger.error("whisper_transcription_failed", error=str(e))
            raise
