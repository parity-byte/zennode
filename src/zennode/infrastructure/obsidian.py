import os
import re

import structlog

from zennode.core.interfaces import IStorageProvider

logger = structlog.get_logger(__name__)

class ObsidianConnector(IStorageProvider):
    """Handles parsing and strictly appending structured AI outputs to Obsidian dump files."""
    
    def read_dump_context(self, filepath: str) -> tuple[str, list[str], str | None]:
        """Reads the Markdown file containing the initial dump.
        Extracts raw text, image paths, and explicitly looks for an embedded audio file.
        """
        if not os.path.exists(filepath):
            logger.error("obsidian_file_not_found", path=filepath)
            raise FileNotFoundError(f"Obsidian dump file not found: {filepath}")
            
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        images: list[str] = []
        base_dir = os.path.dirname(filepath)
        
        # Match standard Obsidian image embeds: ![[image.png]]
        image_pattern = re.compile(r"!\[\[(.*?\.(?:png|jpg|jpeg|gif|webp))\]\]", re.IGNORECASE)
        matches = image_pattern.findall(content)
        
        for img_name in matches:
            img_path = os.path.join(base_dir, img_name)
            if os.path.exists(img_path):
                images.append(img_path)
                logger.info("obsidian_image_path_extracted", image_name=img_name)
            else:
                logger.warning("obsidian_image_missing", expected_path=img_path)

        audio_path: str | None = None
        audio_pattern = re.compile(r"!\[\[(.*?\.(?:webm|ogg|mp3|m4a|wav))\]\]", re.IGNORECASE)
        audio_matches = audio_pattern.findall(content)
        
        if audio_matches:
            # Take the first embedded audio file found
            candidate_audio = os.path.join(base_dir, audio_matches[0])
            if os.path.exists(candidate_audio):
                audio_path = candidate_audio
                logger.info("obsidian_audio_extracted", audio_name=audio_matches[0])
            else:
                logger.warning("obsidian_audio_missing", expected_path=candidate_audio)

        return content, images, audio_path

    def upsert_topic_file(self, vault_path: str, topic_title: str, content_to_write: str, raw_context: str) -> str:
        """
        Writes or completely overwrites a Zettelkasten-style topic file in the Obsidian Vault.
        It keeps the daily raw context at the top for reference, then strictly rewrites the 
        Mastery Sheet structure so it's always up-to-date and never just blindly appended.
        """
        from datetime import datetime
        
        # Sanitize filename
        topic_filename = re.sub(r'[^a-zA-Z0-9_\- ]', '', topic_title).strip()
        topic_filename = topic_filename.replace(' ', '_') + ".md"
        
        topics_dir = os.path.join(vault_path, "Topics")
        os.makedirs(topics_dir, exist_ok=True)
        
        filepath = os.path.join(topics_dir, topic_filename)
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        full_content = f"# 🧠 Topic: {topic_title}\n\n> *Last updated: {date_str} via AuDHD Pipeline*\n\n---\n\n### 🎙️ Latest Raw Dump Context\n{raw_context.strip()}\n\n---\n\n{content_to_write}"
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_content)
            logger.info("obsidian_topic_upserted_success", path=filepath)
            return filepath
        except Exception as e:
            logger.error("obsidian_topic_upsert_failed", path=filepath, error=str(e))
            raise
