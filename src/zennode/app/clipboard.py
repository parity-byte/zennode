
import pyperclip
from PIL import ImageGrab


class ClipboardExtractor:
    @staticmethod
    def extract_text() -> str:
        """Extracts text from the MacOS clipboard."""
        return str(pyperclip.paste())

    @staticmethod
    def extract_image(save_path: str) -> bool:
        """Grabs image from clipboard. Returns True if saved, False if no image."""
        try:
            img = ImageGrab.grabclipboard()
            if img is not None:
                # Can be a list of paths if files were copied, or an Image object
                if isinstance(img, list):
                    # We might handle file copies later. For now, we just want actual images in the clipboard buffer.
                    return False
                img.save(save_path, 'PNG')
                return True
        except Exception as e:
            print(f"Clipboard image extraction failed: {e}")
        return False
