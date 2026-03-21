from abc import ABC, abstractmethod


class IStorageProvider(ABC):
    """Interface for storage backends (Obsidian, Notion, Logseq, etc.)."""
    
    @abstractmethod
    def read_dump_context(self, filepath: str) -> tuple[str, list[str], str | None]:
        """
        Reads the dump context.
        Returns a tuple of (raw_text, list_of_image_paths, embedded_audio_path_if_any).
        """
        pass
        
    @abstractmethod
    def upsert_topic_file(self, vault_path: str, topic_title: str, content_to_write: str, raw_context: str) -> str:
        """
        Writes or completely overwrites a Zettelkasten-style topic file.
        Returns the absolute filepath of the created file.
        """
        pass

class ITranscriptionService(ABC):
    """Interface for Audio Transcription Services (Whisper, Groq, local, etc.)."""
    
    @abstractmethod
    def transcribe(self, audio_file_path: str) -> str:
        """
        Transcribes audio from a given file path.
        Returns the transcription string.
        """
        pass
