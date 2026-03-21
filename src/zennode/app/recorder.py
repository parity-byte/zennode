import queue
import threading
from typing import Any

import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    def __init__(self, samplerate: int = 44100, channels: int = 1) -> None:
        self.samplerate = samplerate
        self.channels = channels
        self.q: queue.Queue[Any] = queue.Queue()
        self.recording = False
        self._thread: threading.Thread | None = None

    def _callback(self, indata: Any, frames: int, time: Any, status: Any) -> None:
        """This is called for each audio block."""
        if status:
            print(f"Audio status: {status}")
        self.q.put(indata.copy())

    def _record_thread(self, filename: str) -> None:
        with sf.SoundFile(filename, mode='x', samplerate=self.samplerate,
                          channels=self.channels, subtype='PCM_24') as file:
            with sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=self._callback):
                while self.recording:
                    try:
                        file.write(self.q.get(timeout=0.1))
                    except queue.Empty:
                        pass
        print(f"Recording saved to {filename}")

    def start_recording(self, filename: str) -> None:
        self.recording = True
        self.q = queue.Queue() # reset queue
        self._thread = threading.Thread(target=self._record_thread, args=(filename,))
        self._thread.start()

    def stop_recording(self) -> None:
        self.recording = False
        if self._thread:
            self._thread.join()
