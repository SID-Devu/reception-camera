"""
Reception Greeter – Text-to-Speech engine.

Uses pyttsx3 for fully offline, low-latency speech synthesis.
Runs TTS in a background thread so it never blocks the vision pipeline.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class TTSEngine:
    """
    Offline text-to-speech using pyttsx3.

    All ``speak()`` calls are non-blocking – messages are queued and
    processed sequentially in a daemon thread.
    """

    def __init__(self, rate: int = 170, volume: float = 0.9) -> None:
        self._rate = rate
        self._volume = volume
        self._queue: queue.Queue[Optional[str]] = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        logger.info("TTS engine started  rate=%d  volume=%.1f", rate, volume)

    def _worker(self) -> None:
        """Background worker that processes the speech queue.

        Reinitialises pyttsx3 for **every** utterance to work around a
        known Windows COM bug where ``runAndWait()`` returns instantly
        after the first call without producing any audio.
        """
        import pyttsx3

        while True:
            text = self._queue.get()
            if text is None:
                self._queue.task_done()
                break  # Shutdown signal
            try:
                logger.info("TTS speaking: %s", text)
                engine = pyttsx3.init()
                engine.setProperty("rate", self._rate)
                engine.setProperty("volume", self._volume)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                del engine
                logger.info("TTS finished: %s", text)
            except Exception:
                logger.exception("TTS error for text: %s", text)
            finally:
                self._queue.task_done()

    def speak(self, text: str) -> None:
        """Queue a message for speech (non-blocking)."""
        self._queue.put(text)

    def wait_and_shutdown(self, timeout: float = 15.0) -> None:
        """Wait for all queued speech to finish, then stop the worker."""
        logger.info("TTS draining queue (%d items) …", self._queue.qsize())
        try:
            self._queue.join()  # blocks until every item is processed
        except Exception:
            logger.warning("TTS queue drain interrupted")
        self._queue.put(None)  # sentinel → worker exits
        self._thread.join(timeout=timeout)
        logger.info("TTS engine shut down (graceful)")

    def shutdown(self) -> None:
        """Stop the TTS worker thread immediately."""
        self._queue.put(None)
        self._thread.join(timeout=5.0)
        logger.info("TTS engine shut down")
