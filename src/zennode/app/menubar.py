import datetime
import subprocess
import threading
import time
import webbrowser
import queue
import os
import dotenv
from pathlib import Path
from typing import Any

import psutil
import rumps

from zennode.infrastructure.config import Config
from zennode.infrastructure.analytics import AnalyticsTracker

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

# Cache the current process object once at startup — cheap to query later
_SELF_PROCESS = psutil.Process()

class StudyPipelineApp(rumps.App): # type: ignore
    def __init__(self) -> None:
        super().__init__("ZenNode", template=True, quit_button="Quit")
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.assets_dir = Path(__file__).resolve().parent.parent / "assets"
        
        # Reliable brain emoji
        self.title = "🧠"
        self.icon = None
        
        self.state = "idle"
        self.animation_thread = None
        
        # --- Background Job Queue ---
        self.job_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._queue_worker, daemon=True)
        self.worker_thread.start()

        self.recorder = AudioRecorder()
        self.is_recording = False
        self.current_dump_dir: Path | None = None
        self._recording_start_time: float = 0.0
        
        # === DASHBOARD METRICS SECTION ===
        # These are user-centric: "what did I accomplish?"
        self.capture_button = rumps.MenuItem("🔴 Start Capture", callback=self.toggle_recording)
        self.status_label = rumps.MenuItem("Status: Idle")
        
        self.profile_menu = rumps.MenuItem("👤 Active Profile")
        
        self.metric_syntheses = rumps.MenuItem("📝 Notes Synthesized: 0")
        self.metric_audio_time = rumps.MenuItem("🎙️ Total Audio Captured: 0s")
        self.metric_errors = rumps.MenuItem("⚠️ Total Errors: 0")
        
        # === SYSTEM STATS SECTION ===
        # Shows how much this APP uses — not the whole system.
        # The small ↻ sits inline as a submenu title hack (rumps limitation workaround):
        # we add it as the last item in the section so it appears just below sys stats.
        self.sys_cpu = rumps.MenuItem("💻 ZenNode CPU: --%")
        self.sys_ram = rumps.MenuItem("🧠 ZenNode RAM: -- MB")
        
        # Tiny refresh — just an icon, no extra text. Lives in a mini separator group.
        self.refresh_icon_btn = rumps.MenuItem("↻", callback=self.manual_refresh)
        
        self.open_vault_button = rumps.MenuItem("📂 Open Vault in Finder", callback=self.open_vault)
        self.star_github = rumps.MenuItem("⭐ Star on GitHub", callback=self.open_github)
        
        self.menu = [
            self.capture_button,
            self.status_label,
            rumps.separator,
            self.profile_menu,
            rumps.separator,
            # --- What you've accomplished ---
            self.metric_syntheses,
            self.metric_audio_time,
            self.metric_errors,
            rumps.separator,
            # --- How the app is running ---
            self.sys_cpu,
            self.sys_ram,
            self.refresh_icon_btn,
            rumps.separator,
            self.open_vault_button,
            self.star_github,
        ] # type: ignore

        self._load_profiles()
        
        # Ensure inbox dir exists, then fire initial stat reads
        INBOX_RAW_DIR.mkdir(parents=True, exist_ok=True)
        self.update_analytics()
        self.update_system_stats()

    def manual_refresh(self, sender: Any) -> None:
        """Manual reload triggered by the ↻ icon."""
        self.update_system_stats()
        self.update_analytics()

    # Auto-refreshes every 5 seconds — shows app-specific process usage
    @rumps.timer(5)
    def refresh_system_stats(self, _):
        self.update_system_stats()

    # Analytics refresh every 60 seconds (metrics file read is heavier)
    @rumps.timer(60)
    def refresh_analytics(self, _):
        self.update_analytics()

    def update_system_stats(self):
        """
        GLASS BOX: We call psutil on this specific process (PID), NOT the whole system.
        _SELF_PROCESS.cpu_percent() returns % of a single CPU core. On M1/M2 which
        have efficiency cores, the value is correctly normalised vs num CPU cores.
        memory_info().rss is the real resident set size — how much RAM the kernel
        has actually mapped for this process. This does NOT include shared lib memory.
        """
        try:
            # cpu_percent tracks delta since last call — must cache the Process object
            app_cpu = _SELF_PROCESS.cpu_percent(interval=None)
            app_ram_mb = int(_SELF_PROCESS.memory_info().rss / (1024 * 1024))
            self.sys_cpu.title = f"💻 ZenNode CPU: {app_cpu:.1f}%"
            self.sys_ram.title = f"🧠 ZenNode RAM: {app_ram_mb} MB"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def open_vault(self, sender: Any) -> None:
        try:
            vault_path = Config.get_obsidian_vault_path()
            if vault_path and Path(vault_path).exists():
                subprocess.Popen(["open", vault_path])
            else:
                subprocess.Popen(["open", str(INBOX_RAW_DIR)])
        except Exception as e:
            rumps.notification("ZenNode Error", "Finder Error", str(e))

    def open_github(self, sender: Any) -> None:
        webbrowser.open("https://github.com/parity-byte/zennode")

    def update_analytics(self):
        """Reads the lightweight JSON metrics store and pushes values into menu items."""
        metric_file = INBOX_RAW_DIR.parent / "metrics.json"
        if metric_file.exists():
            import json
            try:
                with open(metric_file, "r") as f:
                    data = json.load(f)
                self.metric_syntheses.title = f"📝 Notes Synthesized: {data.get('total_syntheses', 0)}"
                # Show human-readable audio time, not raw seconds
                total_secs = data.get("total_audio_seconds", 0.0)
                self.metric_audio_time.title = f"🎙️ Total Audio Captured: {AnalyticsTracker.format_duration(total_secs)}"
                self.metric_errors.title = f"⚠️ Total Errors: {data.get('total_errors', 0)}"
            except Exception:
                pass

    def _load_profiles(self) -> None:
        """Reads Markdown templates from ~/.zennode/templates."""
        current_profile = os.environ.get("ZENNODE_PROFILE", "zennode_audhd_deep_dive.md")
        self.profile_menu.title = f"👤 Profile: {current_profile.replace('.md', '')}"
        
        templates_dir = Path(Config.get_templates_path())
        if templates_dir.exists():
            for p in templates_dir.glob("*.md"):
                item = rumps.MenuItem(p.stem, callback=self.change_profile)
                setattr(item, "template_filename", p.name)
                item.state = 1 if p.name == current_profile else 0
                self.profile_menu.add(item)

    def change_profile(self, sender: rumps.MenuItem) -> None:
        """Switch the active LLM persona dynamically — persisted to .env."""
        env_path = Path.home() / ".zennode" / ".env"
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.touch(exist_ok=True)
        
        filename = getattr(sender, "template_filename")
        for item in self.profile_menu.values():
            item.state = 0
        sender.state = 1
        self.profile_menu.title = f"👤 Profile: {sender.title}"
        dotenv.set_key(str(env_path), "ZENNODE_PROFILE", filename)
        os.environ["ZENNODE_PROFILE"] = filename

    def update_state(self, new_state: str) -> None:
        self.state = new_state
        if new_state == "idle":
            self.title = "🧠"
        elif new_state == "recording":
            self.title = "🔴"
        elif new_state == "error":
            self.title = "❌"
        elif new_state == "processing" and not (self.animation_thread and self.animation_thread.is_alive()):
            self.animation_thread = threading.Thread(target=self._animate_processing)
            self.animation_thread.daemon = True
            self.animation_thread.start()

    def _animate_processing(self) -> None:
        frames = ["⏳", "⌛️"]
        frame_idx = 0
        while self.state == "processing":
            qsize = self.job_queue.qsize()
            pending = f" ({qsize+1} left)" if qsize > 0 else ""
            self.title = f"{frames[frame_idx]}{pending}"
            frame_idx = (frame_idx + 1) % len(frames)
            time.sleep(0.5)

    def toggle_recording(self, sender: Any) -> None:
        if not self.is_recording:
            self.is_recording = True
            self._recording_start_time = time.monotonic()
            sender.title = "⏹️ Stop Capture & Synthesize"
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            self.current_dump_dir = INBOX_RAW_DIR / f"dump_{timestamp}"
            self.current_dump_dir.mkdir(parents=True, exist_ok=True)
            audio_path = self.current_dump_dir / "audio.wav"
            self.recorder.start_recording(str(audio_path))
            rumps.notification(title="ZenNode Pipeline", subtitle="Recording Started", message="Capturing audio...")
            self.update_state("recording")
        else:
            self.is_recording = False
            sender.title = "🔴 Start Capture"
            self.update_state("idle")
            
            # Measure the audio duration for the analytics tracker
            audio_duration_seconds = time.monotonic() - self._recording_start_time
            self.recorder.stop_recording()
            
            text = ClipboardExtractor.extract_text()
            if text and text.strip() and self.current_dump_dir:
                with open(self.current_dump_dir / "clipboard.txt", "w", encoding="utf-8") as f:
                    f.write(text)
                    
            if self.current_dump_dir:
                ClipboardExtractor.extract_image(str(self.current_dump_dir / "clipboard_image.png"))
            
            rumps.notification(title="ZenNode Pipeline", subtitle="Recording Stopped", message="Spawning synthesis in background...")
            
            if self.current_dump_dir:
                self._spawn_pipeline_async(str(self.current_dump_dir), audio_duration_seconds)

    def _spawn_pipeline_async(self, dump_dir: str, audio_duration_seconds: float = 0.0) -> None:
        """Immediately adds the dump to the background queue, passing audio duration for analytics."""
        self.job_queue.put((dump_dir, audio_duration_seconds))
        if self.state != "processing":
            self.update_state("processing")
            
    def _queue_worker(self) -> None:
        """Runs sequentially to process all background dumps without freezing macOS."""
        while True:
            job = self.job_queue.get()
            
            # Handle both old (str) and new (tuple) job formats gracefully
            if isinstance(job, tuple):
                dump_dir, audio_duration_seconds = job
            else:
                dump_dir, audio_duration_seconds = job, 0.0
                
            try:
                if self.state != "processing":
                    self.update_state("processing")
                    
                # V2 Optimization: Compress the heavy WAV to AAC/M4A before sending to LLM
                audio_wav = Path(dump_dir) / "audio.wav"
                audio_m4a = Path(dump_dir) / "audio.m4a"
                if audio_wav.exists():
                    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(audio_wav), str(audio_m4a)])
                    if audio_m4a.exists():
                        audio_wav.unlink()  # Delete the massive uncompressed file
                        
                result = subprocess.run(
                    ["uv", "run", "python", "-m", "zennode.cli.main", "process-dump", dump_dir],
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Pipeline failed: {result.stderr}")
                    AnalyticsTracker.track_error()
                    self.update_analytics()
                    self.update_state("error")
                    rumps.notification(
                        title="ZenNode Error", 
                        subtitle="Synthesis Failed", 
                        message="Please check the terminal logs."
                    )
                else:
                    # Track success with accurate audio duration
                    AnalyticsTracker.track_success(audio_duration_seconds=audio_duration_seconds)
                    self.update_analytics()
                    rumps.notification(
                        title="ZenNode Pipeline", 
                        subtitle="Synthesis Complete", 
                        message="Your new topic is ready in Obsidian!"
                    )
            except Exception as e:
                print(f"Failed to run pipeline worker: {e}")
                AnalyticsTracker.track_error()
                self.update_analytics()
                self.update_state("error")
                rumps.notification(
                    title="ZenNode Error", 
                    subtitle="Queue Error", 
                    message=str(e)
                )
            finally:
                self.job_queue.task_done()
                if self.job_queue.empty() and self.state != "error":
                    self.update_state("idle")

def main() -> None:
    StudyPipelineApp().run()

if __name__ == "__main__":
    main()
