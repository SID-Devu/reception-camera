"""
Reception Greeter – Text-to-Speech engine.

Uses pyttsx3 for fully offline, low-latency speech synthesis.
Runs TTS in a background thread so it never blocks the vision pipeline.

Platform notes:
- Windows: Uses SAPI5 (native speaker)
- macOS: Uses AVFoundation (NSSpeechSynthesizer)
- Linux: Uses espeak (requires package: sudo apt install espeak)
"""

from __future__ import annotations

import logging
import platform
import queue
import threading
import time
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
        self._rate_macos = rate - 20  # macOS speech is slower, compensate
        self._volume = volume
        self._queue: queue.Queue[Optional[str]] = queue.Queue()
        self._os = platform.system()  # "Windows", "Darwin" (macOS), "Linux"
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        logger.info("TTS engine started on %s  rate=%d  volume=%.1f", self._os, rate, volume)

    def _worker(self) -> None:
        """Background worker that processes the speech queue.

        Uses OS-specific speech synthesis:
        - Windows: SAPI5 with per-utterance engine reinitialization (COM bug workaround)
        - macOS: AVFoundation with extra waiting (runAndWait() often returns early)
        - Linux: espeak backend
        """
        import pyttsx3

        while True:
            text = self._queue.get()
            if text is None:
                self._queue.task_done()
                break  # Shutdown signal
            try:
                logger.info("TTS speaking: %s", text)
                
                if self._os == "Darwin":  # macOS
                    self._speak_macos(pyttsx3, text)
                else:  # Windows, Linux, etc.
                    self._speak_generic(pyttsx3, text)
                    
                logger.info("TTS finished: %s", text)
            except Exception:
                logger.exception("TTS error for text: %s", text)
            finally:
                self._queue.task_done()

    def _speak_generic(self, pyttsx3, text: str) -> None:
        """Generic TTS for Windows and Linux."""
        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)
        engine.setProperty("volume", self._volume)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        del engine

    def _speak_macos(self, pyttsx3, text: str) -> None:
        """
        macOS AVFoundation speech synthesis.
        
        Challenges:
        - AVFoundation's runAndWait() may return immediately without actually finishing
        - Volume setting is often ignored by system mixer
        - Speech rate seems slower than on Windows
        
        Workaround: Estimate speech duration and wait extra time.
        """
        engine = pyttsx3.init()
        try:
            # Compensate for slower macOS speech
            engine.setProperty("rate", self._rate_macos)
            engine.setProperty("volume", min(1.0, self._volume))
            
            # Estimate duration: ~150 WPM = 2.5 words/sec = ~500ms per word
            word_count = max(1, len(text.split()))
            estimated_secs = (word_count / self._rate_macos) * 60.0
            
            engine.say(text)
            engine.runAndWait()
            
            # macOS often returns from runAndWait() before audio finishes
            # Add extra wait time (estimated duration + safety margin)
            time.sleep(max(estimated_secs + 0.5, 1.0))
        finally:
            engine.stop()
            del engine

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
