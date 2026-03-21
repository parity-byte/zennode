import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv() # Load local .env first
load_dotenv(Path.home() / ".audhd" / ".env") # Load global .env

class Config:
    @staticmethod
    def get_groq_api_key() -> str:
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY environment variable is missing.")
        return key

    @staticmethod
    def get_gemini_api_key() -> str:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY environment variable is missing.")
        return key

    @staticmethod
    def get_openrouter_api_key() -> str:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY environment variable is missing.")
        return key

    @staticmethod
    def get_obsidian_vault_path() -> str:
        path = os.environ.get("OBSIDIAN_VAULT_PATH")
        if not path:
            raise ValueError("OBSIDIAN_VAULT_PATH environment variable is missing.")
        if not os.path.exists(path):
            raise ValueError(f"Obsidian vault path does not exist: {path}")
        return path

    @staticmethod
    def get_inbox_path() -> str:
        path = os.environ.get("AUDHD_INBOX_PATH")
        if not path:
            path = os.path.expanduser("~/.audhd/inbox")
        os.makedirs(os.path.join(path, "Raw Capture"), exist_ok=True)
        return path
