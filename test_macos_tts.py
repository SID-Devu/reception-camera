#!/usr/bin/env python3
"""
Quick macOS TTS test script.

Run this on macOS to verify audio output:
    python test_macos_tts.py
"""

import sys
import time
from app.audio.tts import TTSEngine

def test_macos_tts():
    """Test TTS engine on the current platform."""
    print(f"Platform: {sys.platform}")
    print("Creating TTS engine...")
    
    tts = TTSEngine(rate=170, volume=0.9)
    
    # Test 1: Simple greeting
    print("\n[Test 1] Speaking: 'Hello, I am ready'")
    tts.speak("Hello, I am ready")
    time.sleep(3)
    
    # Test 2: Person greeting
    print("\n[Test 2] Speaking: 'Welcome Sudheer'")
    tts.speak("Welcome Sudheer")
    time.sleep(3)
    
    # Test 3: Exit greeting
    print("\n[Test 3] Speaking: 'Goodbye Sudheer, see you later'")
    tts.speak("Goodbye Sudheer, see you later")
    
    # Wait for final utterance and shutdown
    print("\n[Shutdown] Waiting for all utterances to finish...")
    tts.wait_and_shutdown(timeout=10.0)
    
    print("\n✅ TTS test completed!")

if __name__ == "__main__":
    test_macos_tts()
