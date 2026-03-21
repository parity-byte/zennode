import datetime
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import rumps

from zennode.infrastructure.config import Config

from .clipboard import ClipboardExtractor
from .recorder import AudioRecorder

# Try to import PyObjC for native Apple icon sizing
try:
    from AppKit import NSImage, NSSize
    HAS_PYOBJC = True
except ImportError:
    HAS_PYOBJC = False

# OpenViking Context Filesystem structure
INBOX_RAW_DIR = Path(Config.get_inbox_path())

class StudyPipelineApp(rumps.App): # type: ignore
    def __init__(self) -> None:
        super().__init__("AuDHD", template=True, quit_button="Quit")
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.assets_dir = Path(__file__).resolve().parent.parent / "assets"
        
        # Emergency rollback to reliable brain emoji
        self.title = "🧠"
        self.icon = None
        
        self.state = "idle"
        self.animation_thread = None


        self.recorder = AudioRecorder()
        self.is_recording = False
        self.current_dump_dir: Path | None = None
        self.record_button = rumps.MenuItem("Start Capture", callback=self.toggle_recording)
        self.menu = [self.record_button] # type: ignore
        INBOX_RAW_DIR.mkdir(parents=True, exist_ok=True)

    def update_state(self, new_state: str) -> None:
        self.state = new_state
        
        if new_state == "idle":
            self.title = "🧠"
        elif new_state == "recording":
            self.title = "🔴"
        elif new_state == "error":
            self.title = "❌"
        elif new_state == "processing":
            self.animation_thread = threading.Thread(target=self._animate_processing)
            self.animation_thread.daemon = True
            self.animation_thread.start()

    def _animate_processing(self) -> None:
        frames = ["⏳", "⌛️"]
        frame_idx = 0
        while self.state == "processing":
            self.title = frames[frame_idx]
            frame_idx = (frame_idx + 1) % len(frames)
            time.sleep(0.5)

    def toggle_recording(self, sender: Any) -> None:
        if not self.is_recording:
            self.is_recording = True
            sender.title = "Stop Capture & Synthesize"
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            self.current_dump_dir = INBOX_RAW_DIR / f"dump_{timestamp}"
            self.current_dump_dir.mkdir(parents=True, exist_ok=True)
            
            audio_path = self.current_dump_dir / "audio.wav"
            self.recorder.start_recording(str(audio_path))
            rumps.notification(title="AuDHD Pipeline", subtitle="Recording Started", message="Capturing audio...")
            self.update_state("recording")
        else:
            self.is_recording = False
            sender.title = "Start Capture"
            self.update_state("idle")
            
            self.recorder.stop_recording()
            
            text = ClipboardExtractor.extract_text()
            if text and text.strip() and self.current_dump_dir:
                with open(self.current_dump_dir / "clipboard.txt", "w", encoding="utf-8") as f:
                    f.write(text)
                    
            if self.current_dump_dir:
                ClipboardExtractor.extract_image(str(self.current_dump_dir / "clipboard_image.png"))
            
            rumps.notification(title="AuDHD Pipeline", subtitle="Recording Stopped", message="Audio and Clipboard captured. Spawning synthesis...")
            
            if self.current_dump_dir:
                self._spawn_pipeline_async(str(self.current_dump_dir))

    def _spawn_pipeline_async(self, dump_dir: str) -> None:
        def run_proc() -> None:
            self.update_state("processing")
            try:
                result = subprocess.run(
                    ["uv", "run", "audhd-pipeline", "process-dump", dump_dir],
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Pipeline failed: {result.stderr}")
                    self.update_state("error")
                    rumps.notification(
                        title="AuDHD Pipeline Error", 
                        subtitle="Synthesis Failed", 
                        message="Check the console or logs for details."
                    )
                else:
                    self.update_state("idle")
                    rumps.notification(
                        title="AuDHD Pipeline", 
                        subtitle="Synthesis Complete", 
                        message="Your new topic is ready in Obsidian!"
                    )
            except Exception as e:
                print(f"Failed to spawn pipeline: {e}")
                self.update_state("error")
                rumps.notification(
                    title="AuDHD Pipeline Error", 
                    subtitle="System Error", 
                    message=f"Could not launch background process."
                )

        threading.Thread(target=run_proc).start()

def main() -> None:
    StudyPipelineApp().run()

if __name__ == "__main__":
    main()
