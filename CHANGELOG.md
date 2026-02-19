# Changelog

All notable changes to the Reception Greeter project will be documented in this file.

## [1.2.0] - Installation Improvements & Beginner Documentation

### Added
- **install.py** - Cross-platform Python installer script
  - Auto-detects Windows and applies `--prefer-binary` flag
  - Solves insightface C++ build requirement on Windows + Python 3.12
  - Verifies all imports after installation
  - Shows installation status and next steps
  
- **install_windows.bat** - One-click Windows batch installer
  - Automatically activates virtual environment
  - Runs pip with `--prefer-binary` for prebuilt binaries
  - Clear success/error messaging
  - Ideal for non-technical users

- **Completely redesigned README.md** for beginners
  - 🎯 Quick Overview with plain-language feature descriptions
  - ✅ Before You Start checklist with verification tests
  - 📋 Prerequisites table with laptop type performance expectations
  - 🚀 5 crystal-clear installation steps with expected outputs
  - 👨‍💼 For Engineers section with testing & development guide
  - 🧪 For Manual Testers section with 6 comprehensive test scenarios
  - Test Results template for documentation
  - 🛠️ Enhanced troubleshooting with actual command solutions
  - 📖 Full commands reference
  - ⚙️ Configuration section for advanced users
  - 🔧 Advanced tuning parameters table
  - 🏗️ Project architecture diagram
  - Estimated timing for each installation step (10-15 minutes total)

### Changed
- README structure reorganized for beginner-to-advanced user flow
- Installation instructions now account for old/mid-range/gaming laptops
- Troubleshooting section expanded with platform-specific solutions
- Test documentation includes checklist template for manual testers

### Version Updates
- pyproject.toml: 1.0.0 → 1.2.0
- README.md: 1.1.0 → 1.2.0

## [1.1.0] - macOS TTS Support

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

