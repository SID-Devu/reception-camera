# Changelog

All notable changes to the Reception Greeter project will be documented in this file.

## [1.3.0] - README Rewrite, User Guide Audit, Documentation Accuracy

### Changed
- **README.md completely rewritten**
  - Removed all emojis for clean, professional documentation
  - Added "Quick Start (All Platforms)" section at the top with one-command setup
  - Separate clear paths for Windows, Linux/macOS, and edge devices
  - Added "Supported Platforms" table (Windows, macOS Intel/ARM, Ubuntu, RB5, RPi, Jetson)
  - Updated architecture diagram with all new scripts (setup_rb5.sh, deploy_rb5.sh, validate.sh, docker/, docs/)
  - Added "Post-Setup Validation" commands reference
  - Version updated to 1.3.0
  - Fresh-engineer friendly: a new developer can go from zero to running in one command

### Fixed (User Guide Cross-Reference Audit)
All scripts and docs audited against the 89-page Qualcomm RB5 User Guide (80-88500-5 Rev. AF):

- **setup_rb5.sh - DIP switch table corrected:**
  - Pin 5: Fixed from "IMU sensor ON (default)" to "OFF = SPI to onboard IMU; ON = SPI to LS3 connector"
  - Pin 4: Expanded to "OFF = DSI0 to HDMI bridge (LT9611UCX); ON = DSI0 to HS1 connector"
  - Added Vision Mezzanine DIP2 Pin 2 note (required ON for DMIC recording)
- **setup_rb5.sh - Added tinyALSA DMIC recording path:**
  - 4 commands using DMIC3 (not DMIC2 like the ALSA path), per User Guide page 66
- **setup_rb5.sh - SoC specs corrected:**
  - "Hexagon 698" changed to "Hexagon DSP" (PDF does not specify model number)
  - "Qualcomm AI Engine" changed to "NPU230" (per PDF naming)
- **RB5_DEPLOYMENT.md - DMIC section fixed:**
  - Added missing SampleRate and Format commands for full 8-command ALSA DMIC path
  - Added tinyALSA DMIC alternative (4 commands with DMIC3)
- **RB5_DEPLOYMENT.md - wpa_supplicant.conf fixed:**
  - Removed ctrl_interface/update_config (not in PDF)
  - Added pairwise=TKIP CCMP and group=TKIP CCMP fields (per PDF)
- **RB5_DEPLOYMENT.md - Hardware specs corrected:**
  - HDMI: "HDMI 1.4, 4K30" changed to "HDMI (LT9611UCX bridge), 4K at 60 Hz"
  - DSP: "Hexagon 698" changed to "Hexagon DSP"
  - NPU: "Qualcomm AI Engine" changed to "NPU230"
- **RB5_DEPLOYMENT.md - GStreamer pipelines fixed:**
  - Added (memory:GBM) caps annotation for hardware-accelerated zero-copy GPU buffer paths
  - Added camera index mapping: camera=0 = IMX577, camera=1 = OV9282
- **RB5_DEPLOYMENT.md - DIP switch table:**
  - Same Pin 4/5 corrections as setup_rb5.sh
  - Added Vision Mezzanine DIP2 note

### Version Updates
- README.md: 1.2.0 -> 1.3.0

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

