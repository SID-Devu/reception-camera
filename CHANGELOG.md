# Changelog

All notable changes to the Reception Greeter project will be documented in this file.

## [1.0.1] - macOS TTS Support

### Added
- **Cross-platform TTS support** for Windows, macOS, and Linux
  - Windows: SAPI5 (native speaker)
  - macOS: AVFoundation (NSSpeechSynthesizer)
  - Linux: espeak
- OS-aware TTS engine that automatically adapts to the current platform
- macOS-specific workarounds for AVFoundation audio timing issues
- Speech rate auto-compensation for macOS (slower platform)
- Test script `test_macos_tts.py` for verifying TTS on any platform
- Detailed macOS troubleshooting guide in README

### Fixed
- **macOS audio not playing:** Added estimated duration waiting to work around AVFoundation's `runAndWait()` returning early
- TTS engine now detects platform (`platform.system()`) and uses appropriate backends

### Technical Details

**macOS Audio Challenge:**
- AVFoundation's `runAndWait()` often returns immediately without waiting for audio to finish
- Volume property is ignored by system mixer (controlled by system volume setting)
- Speech rate appears slower than Windows SAPI

**Solution:**
- Estimate utterance duration based on word count and speech rate
- Wait extra time (estimated_duration + safety_margin) after `runAndWait()` to ensure audio completes
- Reduce speech rate by 20 WPM on macOS to maintain natural speed
- Document system volume control for macOS users

## [1.0.0] - Initial Release (2024)

### Features
- Real-time face recognition and greeting system
- ENTRY and EXIT presence-based events
- Graceful TTS shutdown with queue draining
- Fresh machine model download support
- Clean release with single commit
- Production-ready codebase

