import json
import os
from pathlib import Path
from typing import Dict, Any

from .config import Config

METRICS_FILE = Path(Config.get_inbox_path()).parent / "metrics.json"

class AnalyticsTracker:
    @staticmethod
    def _load_metrics() -> Dict[str, Any]:
        if METRICS_FILE.exists():
            try:
                with open(METRICS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        # Added total_audio_seconds to replace avg_latency (not user-meaningful)
        return {"total_syntheses": 0, "total_errors": 0, "total_audio_seconds": 0.0, "total_runs": 0}

    @staticmethod
    def _save_metrics(metrics: Dict[str, Any]) -> None:
        try:
            with open(METRICS_FILE, "w") as f:
                json.dump(metrics, f)
        except Exception as e:
            print(f"Failed to save metrics: {e}")

    @classmethod
    def track_success(cls, audio_duration_seconds: float = 0.0) -> None:
        """Track a successful synthesis. audio_duration_seconds is the length of the raw audio processed."""
        metrics = cls._load_metrics()
        metrics["total_runs"] = metrics.get("total_runs", 0) + 1
        metrics["total_syntheses"] = metrics.get("total_syntheses", 0) + 1
        # Accumulate total audio time captured in seconds
        metrics["total_audio_seconds"] = metrics.get("total_audio_seconds", 0.0) + audio_duration_seconds
        cls._save_metrics(metrics)

    @classmethod
    def track_error(cls) -> None:
        metrics = cls._load_metrics()
        metrics["total_errors"] = metrics.get("total_errors", 0) + 1
        cls._save_metrics(metrics)

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Convert raw seconds to a human-readable 'Xh Ym' or 'Ym Zs' string."""
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            m, s = divmod(seconds, 60)
            return f"{m}m {s}s"
        else:
            h, rem = divmod(seconds, 3600)
            m = rem // 60
            return f"{h}h {m}m"
