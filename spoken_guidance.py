"""Opt-in macOS speech for application hints, separate from VoiceOver."""

from pathlib import Path
from queue import Empty, Queue
from subprocess import DEVNULL, PIPE, Popen, TimeoutExpired
from sys import platform
from threading import Lock, Thread

SAY_EXECUTABLE = "/usr/bin/say"
MAX_SPEECH_CHARACTERS = 4000


class SpokenGuidance:
    """Speak the newest request without blocking Tk or accumulating old hints."""

    def __init__(self):
        self.available = platform == "darwin" and Path(SAY_EXECUTABLE).is_file()
        self.enabled = False
        self.failed = False
        self.closed = False
        self._lock = Lock()
        self._queue = Queue()
        self._worker = None
        self._process = None
        self._generation = 0

    def set_enabled(self, enabled: bool) -> bool:
        if not enabled:
            self.stop()
            return True
        with self._lock:
            if self.closed or not self.available:
                return False
            self.failed = False
            self.enabled = True
            if self._worker is None:
                self._worker = Thread(target=self._run, daemon=True)
                try:
                    self._worker.start()
                except RuntimeError:
                    self._worker = None
                    self.enabled = False
                    self.failed = True
                    return False
        return True

    def _discard_pending(self):
        while True:
            try:
                self._queue.get_nowait()
            except Empty:
                return

    def _interrupt(self):
        if self._process is not None:
            try:
                if self._process.poll() is None:
                    self._process.terminate()
            except OSError:
                pass

    def speak(self, text: str):
        with self._lock:
            if not self.enabled or self.closed or not text.strip():
                return
            self._discard_pending()
            self._interrupt()
            self._generation += 1
            self._queue.put((self._generation, text[:MAX_SPEECH_CHARACTERS]))

    def stop(self):
        """Mute immediately; the worker reaps its own subprocess."""
        with self._lock:
            self.enabled = False
            self._generation += 1
            self._discard_pending()
            self._interrupt()

    def close(self):
        with self._lock:
            self.closed = True
            self.enabled = False
            self._generation += 1
            self._discard_pending()
            self._interrupt()
            self._queue.put(None)

    def _run(self):
        while True:
            item = self._queue.get()
            if item is None:
                return
            generation, text = item
            process = None
            try:
                with self._lock:
                    if (
                        not self.enabled
                        or self.closed
                        or generation != self._generation
                    ):
                        continue
                    process = Popen(
                        [SAY_EXECUTABLE, "-f", "-"],
                        stdin=PIPE,
                        stdout=DEVNULL,
                        stderr=DEVNULL,
                        text=True,
                        encoding="utf-8",
                    )
                    self._process = process
                try:
                    process.communicate(input=text, timeout=120)
                except TimeoutExpired:
                    process.kill()
                    process.communicate()
                    with self._lock:
                        self.failed = True
                        self.enabled = False
                        self._discard_pending()
                # A terminated utterance is expected when a newer hint replaces it.
                if process.returncode not in (0, -15):
                    with self._lock:
                        if generation == self._generation:
                            self.failed = True
                            self.enabled = False
                            self._discard_pending()
            except OSError:
                if process is not None:
                    try:
                        process.kill()
                        process.communicate()
                    except OSError:
                        pass
                with self._lock:
                    self.failed = True
                    self.enabled = False
                    self._discard_pending()
            finally:
                with self._lock:
                    self._process = None
            if self.closed:
                return
