# Reception Greeter

Real-time face-recognition camera system that **greets people by name** when they arrive and **says goodbye** when they leave. Designed for office receptions, lobbies, and front-desk environments.

**What it does:**
```
Your Camera -> Detects Faces -> Recognizes People -> Plays Audio Greeting
"Hey Alice, welcome! Have a nice day!"
```

---

## Quick Start (All Platforms)

The fastest way to get running. Works on **Windows 10/11**, **macOS** (Intel and Apple Silicon), and **Linux** (Ubuntu/Debian).

### One-Command Setup (Linux / macOS)

```bash
git clone https://github.com/SID-Devu/reception-camera.git
cd reception-camera
chmod +x setup.sh
sudo ./setup.sh
```

The setup script will automatically:
1. Detect your platform and OS
2. Install system dependencies (Python, OpenCV, GStreamer, audio libraries)
3. Create a Python virtual environment
4. Install all Python packages (including insightface, onnxruntime)
5. Download AI models (~350MB, one-time)
6. Configure camera, audio, and display
7. Install a systemd service for auto-start (Linux only)

### Windows Setup

```bash
git clone https://github.com/SID-Devu/reception-camera.git
cd reception-camera

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
python install.py

# Download AI models
python tools/download_models.py

# Run
python app/main.py --config app/config.yaml
```

### Edge Devices: Qualcomm RB5 Deployment (Step-by-Step)

**For other edge devices (Raspberry Pi, NVIDIA Jetson):** Same as Linux setup above.

**For Qualcomm RB5 Development Kit:** Follow this guide if you have the hardware connected via USB-C.

#### Step 1: Install ADB (Android Debug Bridge)

ADB allows you to communicate with the RB5 board from your development machine.

**Windows:**
```powershell
# Download Android SDK Platform Tools
Invoke-WebRequest -Uri "https://dl.google.com/android/repository/platform-tools-latest-windows.zip" -OutFile "$env:TEMP\platform-tools.zip"
Expand-Archive -Path "$env:TEMP\platform-tools.zip" -DestinationPath "C:\Android" -Force

# Add to PATH permanently
$current = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($current -notlike "*Android*") {
  [Environment]::SetEnvironmentVariable('Path', "$current;C:\Android\platform-tools", 'User')
}

# Add for current session
$env:PATH += ";C:\Android\platform-tools"
adb version  # Verify installation
```

**macOS:**
```bash
brew install android-platform-tools
adb version  # Verify
```

**Linux:**
```bash
sudo apt-get install android-tools-adb
adb version  # Verify
```

#### Step 2: Connect RB5 and Verify Connection

1. **Power on the RB5 board**
2. **Connect USB-C debug cable** from RB5 to your development machine
3. **Check connection:**
   ```bash
   adb devices
   # Should show: <serial>  device
   ```

#### Step 3: Clone Project on Your Development Machine

```bash
cd /path/to/projects
git clone https://github.com/SID-Devu/reception-camera.git
cd reception-camera
```

#### Step 4: Deploy to RB5

The deployment script handles file transfer and setup execution.

**Option A: Full Deployment (Recommended)**
```bash
# Linux/macOS:
bash ./scripts/deploy_rb5.sh

# Windows (via Git Bash):
"C:\Program Files\Git\bin\bash.exe" ./scripts/deploy_rb5.sh
```

This will:
- Push all project files to `/opt/reception-camera` on the RB5
- Run the full setup
- Configure audio, camera, display
- Download AI models (~350MB)
- Create systemd service for auto-start

**Option B: Push Files Only**
```bash
bash ./scripts/deploy_rb5.sh --push-only
```

Then manually run setup on the RB5:
```bash
adb shell
cd /opt/reception-camera
sudo ./setup.sh
```

**Option C: SSH Deployment** (if RB5 has network access)
```bash
bash ./scripts/deploy_rb5.sh --ssh root@<RB5_IP_ADDRESS>
```

#### Step 5: Validate Setup

Check that everything installed correctly:

```bash
adb shell "cd /opt/reception-camera && ./scripts/validate.sh"
```

Expected output: **20+ PASS checks**

If you see failures:
```bash
adb shell "cd /opt/reception-camera && ./scripts/validate.sh --fix"
```

#### Step 6: Add Your First Person

Enroll a test person (no display needed for headless mode):

```bash
adb shell "cd /opt/reception-camera && source .venv/bin/activate && python tools/enroll.py --no-display --name 'Alice'"
```

#### Step 7: Start the Service

**Option A: As a system service** (auto-starts on boot)
```bash
adb shell systemctl start reception-greeter
adb shell systemctl status reception-greeter  # Verify running
```

**Option B: Manual run** (for testing)
```bash
adb shell "cd /opt/reception-camera && source .venv/bin/activate && python app/main.py --no-display --config app/config_rb5.yaml"
```

#### Step 8: Monitor Logs

Watch live logs to debug issues:

```bash
adb shell journalctl -u reception-greeter -f
```

### Useful RB5 Commands

```bash
# Check board info
adb shell getprop ro.product.board          # Should be: qrb5165
adb shell df -h                              # Disk space

# Manage service
adb shell systemctl start reception-greeter
adb shell systemctl stop reception-greeter
adb shell systemctl restart reception-greeter

# View service logs
adb shell journalctl -u reception-greeter -n 100

# Run interactive shell
adb shell

# Transfer files
adb push <local-file> /opt/reception-camera/
adb pull /opt/reception-camera/<file> .
```

### Troubleshooting RB5

**ADB connection issues:**
```bash
# Restart ADB server
adb kill-server
adb start-server
adb devices  # Try again

# Check USB cable is in DEBUG port (not charging)
```

**Setup failed:**
```bash
# Check logs
adb shell journalctl -u reception-greeter -n 50

# Re-run setup
adb shell "cd /opt/reception-camera && sudo ./setup.sh"
```

**Service won't start:**
```bash
# Check disk space
adb shell df -h  # Need >2GB free

# Check Python works
adb shell "cd /opt/reception-camera && source .venv/bin/activate && python --version"

# Check imports
adb shell "cd /opt/reception-camera && source .venv/bin/activate && python app/main.py --help"
```

For more details, see [docs/RB5_DEPLOYMENT.md](docs/RB5_DEPLOYMENT.md).

---

## Quick Overview

| Feature | What It Means |
|---------|---------------|
| **Face Detection** | Finds faces in camera feed (works in real-time) |
| **Recognition** | Matches faces to enrolled people by name |
| **Voice Greeting** | Speaks "Welcome Alice" automatically |
| **Goodbye Tracking** | Says goodbye when person leaves |
| **Database** | Saves who visited and when |
| **Works Offline** | No internet required after setup |

---

## Before You Start - Quick Checklist

Before installing, make sure you have:

- [ ] **A webcam** (USB or built-in) that works
- [ ] **Python installed** (3.10+) - [Download here](https://www.python.org/downloads/)
- [ ] **Internet access** (for downloading models on first run)
- [ ] **15-20 minutes** for fresh setup
- [ ] **Optional:** A microphone if you want to hear the greetings

**Unsure about your setup?** Run this quick test first:

```bash
# Check Python version
python --version

# Check your webcam works (press Ctrl+C to exit)
# On Linux: Use this version (avoids bash history expansion issues with !)
python3 << 'EOF'
import cv2
cap = cv2.VideoCapture(0)
if cap.isOpened():
    print("Webcam works!")
else:
    print("Webcam not found")
cap.release()
EOF

# On Windows: Can use this simpler version
python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"
```

---

## Prerequisites

| Item | Requirements | Notes |
|------|--------------|-------|
| **Python** | 3.10, 3.11, 3.12, or 3.13 | [Download Python](https://www.python.org/downloads/) |
| **Webcam** | Any USB or built-in camera | Must be recognized by your OS |
| **OS** | Windows 10/11, macOS, Linux | Fresh installation works on all |
| **Internet** | Needed first time only | ~500MB download for face models |

### For Different Laptop Types

| Laptop Type | What to Expect | Performance |
|------------|---|---|
| **New/Gaming Laptop** | Everything will work smoothly | 30+ FPS, instant recognition |
| **Mid-range Laptop** | Runs well, slight delays possible | 15-20 FPS |
| **Old Laptop (5+ years)** | Will work but slower | 5-10 FPS, might be sluggish |

> **For old laptops:** The system still works but may take 2-3 seconds to recognize someone. This is normal.

---

## Manual Installation (Step by Step)

If you prefer manual setup over `setup.sh`, follow these steps.

**Estimated time:** 10-15 minutes (depending on your internet speed)

### Step 1: Clone the Repository

```bash
git clone https://github.com/SID-Devu/reception-camera.git
cd reception-camera
```

### Step 2: Check Your Python Installation

```bash
# Should show 3.10 or higher
python --version
```

> **Doesn't show version?** [Install Python here](https://www.python.org/downloads/)

### Step 3: Create a Virtual Environment

A virtual environment keeps this project separate from other Python projects on your machine.

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

You'll see `(.venv)` at the start of your prompt when the virtual environment is active.

### Step 4: Install All Dependencies

**Recommended for all platforms** (handles platform-specific issues):

```bash
python install.py
```

**Or manually on Linux/macOS:**

```bash
pip install opencv-python numpy insightface onnxruntime scipy pyttsx3 PyYAML albumentations==1.4.24
```

**Linux users:** If you get build errors for insightface, you may need development headers:

```bash
# Ubuntu/Debian
sudo apt-get install python3-dev python3.12-dev build-essential

# Or use prebuilt wheels (faster)
pip install --prefer-binary insightface opencv-python
```

### Step 5: Download Face Recognition Models

This downloads the face recognition AI (~350MB) once. After this, it's stored locally and works offline.

```bash
python tools/download_models.py
```

---

## For Engineers: Testing and Development

### Quick Test: Run the Live Camera

See if the system works with your camera:

```bash
python app/main.py --config app/config.yaml
```

**What you'll see:**
- Camera feed appears in a window
- Face bounding boxes when faces detected
- Console prints what's happening

**Keyboard controls:**
- `q` - Quit the program
- `r` - Reload faces database (after enrolling new person)
- `ESC` - Also quits

**Test with old camera/no faces:**
> If no faces appear, wait 10-15 seconds. If still nothing, check the console for errors.

### Add Your First Person

```bash
# Mode 1: With camera (visual feedback)
python tools/enroll.py --config app/config.yaml --name "YourName"

# Mode 2: Without camera (SSH or headless)
python tools/enroll.py --config app/config.yaml --name "YourName" --no-display

# Mode 3: Many people quickly
for person in Alice Bob Charlie; do
  python tools/enroll.py --config app/config.yaml --name "$person"
done
```

**What happens:**
1. Camera captures 10-20 face samples from different angles
2. System quality-checks each sample (blur, lighting, face size)
3. Stores the face data in database

### Verify It Works

**Test 1: See who's in the database**

```bash
python tools/admin.py --config app/config.yaml list
```

**Test 2: See recent greetings**

```bash
python tools/admin.py --config app/config.yaml events --limit 10
```

**Test 3: Full end-to-end test**

```bash
python app/main.py --config app/config.yaml
```

Then:
1. Let the system run for 5 seconds
2. Look directly at camera (should see bounding box)
3. Wait 3-5 seconds (does it say your name?)
4. Look away (does it say goodbye?)

---

## For Manual Testers: Testing Checklist

Use this to manually test the system before deployment.

### Pre-Test Setup

1. **Enrol at least 3 test people:**
   ```bash
   python tools/enroll.py --config app/config.yaml --name "Alice"
   python tools/enroll.py --config app/config.yaml --name "Bob"
   python tools/enroll.py --config app/config.yaml --name "Charlie"
   ```

2. **Start the system:**
   ```bash
   python app/main.py --config app/config.yaml
   ```

### Manual Test Scenarios

#### Test 1: Basic Entry Greeting
- [ ] Face appears in camera
- [ ] System shows bounding box
- [ ] Hears: "Hey Alice, welcome! Have a nice day."

**Expected behavior:** Greeting plays in 3-5 seconds

#### Test 2: Exit/Goodbye Greeting
- [ ] Greeted person looks away
- [ ] Wait 3-5 seconds
- [ ] Hears: "Bye Alice, see you later!"

#### Test 3: Multiple People at Once
- [ ] Put 2-3 faces in camera
- [ ] Should recognize all simultaneously
- [ ] Should hear all greetings in sequence

#### Test 4: Old Laptop Test (if available)
- [ ] Run on older machine
- [ ] Should see live feed (might be slower)
- [ ] Recognition should work (5-20 seconds acceptable)

**Note:** Older laptops are 5-10x slower. This is normal and acceptable.

#### Test 5: Repeated Recognition (Cooldown)
- [ ] Greet Alice
- [ ] Alice leaves
- [ ] Alice comes back within 5 minutes
- [ ] Should NOT greet again (5-minute cooldown)
- [ ] After 5 minutes, should greet again

#### Test 6: Database Persistence
- [ ] Check people list: `python tools/admin.py list`
- [ ] Stop system (Ctrl+C)
- [ ] Start system again
- [ ] People list should be identical

### Test Results Template

```
System:        Windows 10 / macOS / Linux
Laptop:        New / Mid-range / Old
Python:        3.12.3
Date:          2025-02-19

Test 1 - Entry Greeting:    PASS / FAIL
Test 2 - Exit Greeting:     PASS / FAIL
Test 3 - Multiple People:   PASS / FAIL
Test 4 - Old Laptop:        PASS / FAIL
Test 5 - Cooldown:          PASS / FAIL
Test 6 - Database:          PASS / FAIL

Issues Found:
- (none) / list here
```

---

## Troubleshooting

### Linux: "python3-venv package not installed"

**Error:** `ensurepip is not available`

**Solution:**

```bash
# Ubuntu/Debian systems
sudo apt-get install python3.12-venv

# Then recreate venv
python3 -m venv .venv
source .venv/bin/activate
```

### Linux: "No module named 'insightface'" after venv creation

**Error:** You created venv but skipped the installation step

**Solution:**

```bash
# Make sure venv is activated
source .venv/bin/activate

# Run the installer
python install.py

# Or manually install
pip install --prefer-binary insightface opencv-python numpy onnxruntime scipy pyttsx3 PyYAML albumentations==1.4.24
```

### "Webcam not found" or "Camera won't open"

```bash
# Check if camera device exists
python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'NOT FOUND')"
```

**Solutions:**
- Reconnect USB webcam (if using external)
- Restart program
- Try different USB port
- In `app/config.yaml`, change `source: 0` to `source: 1` (if multiple cameras)

### "No sound / greeting not playing"

```bash
# Check volume
python -c "import pyttsx3; e = pyttsx3.init(); e.say('test'); e.runAndWait()"
```

**Solutions:**
- Check system volume is on
- Unmute speakers
- Check `app/config.yaml` - `tts.volume: 0.9`
- **macOS:** System volume controls output (set to 50%+ in System Preferences)
- **Linux:** Install espeak: `sudo apt install espeak`

### "Face not recognized"

**Solutions:**
- Improve lighting (move closer to window or light)
- Re-enroll person with better samples
- Increase max samples: `python tools/enroll.py --name "Person" --min-samples 20`
- Lower similarity threshold in `app/config.yaml`: `similarity_threshold: 0.35`

### "Installation failed - Microsoft Visual C++ required"

```bash
# Use this (Windows only)
pip install --prefer-binary insightface opencv-python
```

Or download [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### "ImportError: No module named 'insightface'"

```bash
# Make sure venv is activated
python -c "import insightface; print(insightface.__version__)"

# If still fails, reinstall
pip install --force-reinstall insightface
```

---

## Full Commands Reference

### Starting the System

```bash
# Normal: with camera display
python app/main.py --config app/config.yaml

# Headless: no display (works on SSH / remote machines)
python app/main.py --no-display --config app/config.yaml

# Without audio greetings (silent mode)
python app/main.py --no-tts --config app/config.yaml
```

### Managing People

```bash
# List everyone
python tools/admin.py --config app/config.yaml list

# Show person details
python tools/admin.py --config app/config.yaml info --name "Alice"

# Delete person
python tools/admin.py --config app/config.yaml delete --name "Alice"

# See recent events
python tools/admin.py --config app/config.yaml events --limit 50

# See statistics
python tools/admin.py --config app/config.yaml stats
```

### Database

```bash
# Backup database to JSON
python tools/export_db.py --config app/config.yaml export --output backup.json

# Restore database from JSON
python tools/export_db.py --config app/config.yaml import --input backup.json
```

### Post-Setup Validation

```bash
./scripts/validate.sh          # Full health check
./scripts/validate.sh --quick  # Fast check
./scripts/validate.sh --fix    # Auto-fix issues
./scripts/validate.sh --json   # JSON output
```

---

## Configuration

All settings are in `app/config.yaml`. Edit to customize behavior:

```yaml
camera:
  source: 0                  # Webcam index (0 = default, or RTSP URL)
  width: 1280
  height: 720
  fps: 30

face_detection:
  min_confidence: 0.5        # Higher = stricter face detection
  min_face_size: 60          # Minimum face pixel width

recognition:
  similarity_threshold: 0.40 # Higher = stricter matching (try 0.35 if missing people)
  consecutive_frames_required: 3

greeting:
  mode: "presence"           # "presence" (recommended) or "door_line"
  cooldown_seconds: 300      # 5 minutes between re-greets
  entry_template: "Hey {name}, welcome! Have a nice day."
  exit_template: "Bye {name}, see you later!"

tts:
  engine: "pyttsx3"
  rate: 170                  # Words per minute
  volume: 0.9                # 0.0 (silent) to 1.0 (loud)

performance:
  use_gpu: false             # Set to true if using NVIDIA GPU
```

### Common Tuning Parameters

| Setting | What It Does | Default | Tip |
|---------|------------|---------|-----|
| `similarity_threshold` | How strict face matching is | 0.40 | Lower (0.30) = more lenient |
| `consecutive_frames_required` | Frames before greeting | 3 | Lower = faster greeting |
| `max_frames_missing` | Frames before EXIT event | 8 | Lower = faster goodbye |
| `min_face_size` | Minimum face pixel width | 60 | Lower = detects distant faces |
| `cooldown_seconds` | Time before re-greeting | 300 | Set to 0 to always greet |

---

## How It Works

### The Processing Pipeline

```
Your Camera
    |
Frame arrives at 30 FPS
    |
Every 3rd frame, detect faces using SCRFD
    |
For each face, extract ArcFace feature (512-dim vector)
    |
Compare against database of known faces (cosine similarity)
    |
Track faces across frames using centroid distance
    |
When streak reaches 3 frames: Fire ENTRY event -> Play greeting audio
    |
When face leaves frame: Fire EXIT event -> Play goodbye audio
```

### Key Components

- **Face Detection:** SCRFD model (fast, runs on CPU)
- **Face Recognition:** ArcFace embeddings (512-dimensional vectors)
- **Tracking:** Centroid-based tracking with streak counting
- **Audio:** Background thread TTS engine (doesn't block vision)
- **Database:** SQLite stores faces, embeddings, and visit events

---

## Architecture

```
reception-camera/
|-- app/                           # Main application
|   |-- main.py                    # Entry point (vision pipeline)
|   |-- config.yaml                # Default settings
|   |-- config_rb5.yaml            # RB5-specific settings
|   |-- audio/
|   |   +-- tts.py                 # Text-to-speech engine (background thread)
|   |-- db/
|   |   |-- storage.py             # SQLite database access
|   |   +-- schema.sql             # Database schema
|   |-- hardware/                  # Auto-detection (RPi, RB5, Jetson, x86)
|   |   |-- detector.py            # Platform and accelerator detection
|   |   |-- camera_discovery.py    # USB/CSI/RTSP camera scanning
|   |   +-- audio_discovery.py     # Speaker/audio output discovery
|   +-- vision/
|       |-- camera.py              # Camera reader (background thread)
|       |-- face_detect.py         # SCRFD face detector
|       |-- embedder.py            # ArcFace embedding extractor
|       |-- matcher.py             # Cosine similarity matcher
|       |-- tracker.py             # Centroid tracker
|       +-- events.py              # ENTRY/EXIT event detector
|-- tools/                         # Utility scripts
|   |-- enroll.py                  # Enrol new person
|   |-- admin.py                   # Manage database
|   |-- export_db.py               # Export/import database
|   +-- download_models.py         # Download AI models
|-- scripts/                       # Setup and operations
|   |-- setup_rb5.sh               # RB5 board-level config (audio, camera, display)
|   |-- deploy_rb5.sh              # Deploy from host via ADB or SSH
|   |-- validate.sh                # Post-setup health check
|   |-- benchmark.py               # Pipeline benchmark
|   |-- cleanup_old_data.py        # Cleanup old events
|   |-- seed_db.py                 # Seed test data
|   +-- export_embeddings.py       # Export embeddings to JSON
|-- docker/                        # Container support
|   |-- Dockerfile                 # Standard container image
|   |-- Dockerfile.gpu             # GPU-accelerated image
|   +-- docker-compose.yml         # Multi-service compose
|-- docs/                          # Documentation
|   +-- RB5_DEPLOYMENT.md          # Qualcomm RB5 deployment guide
|-- setup.sh                       # Universal auto-setup (all platforms)
|-- install.py                     # Python dependency installer
|-- Makefile                       # Build targets (run, enroll, test, docker)
|-- data/                          # Stores database
|-- logs/                          # Stores logs
+-- README.md                      # This file
```

---

## Supported Platforms

| Platform | Auto-Setup | Notes |
|----------|-----------|-------|
| **Windows 10/11** | Manual (see Quick Start) | Python + pip, no sudo needed |
| **macOS (Intel)** | `sudo ./setup.sh` | Uses Homebrew for system deps |
| **macOS (Apple Silicon)** | `sudo ./setup.sh` | ARM-native builds |
| **Ubuntu / Debian** | `sudo ./setup.sh` | apt-based, systemd service |
| **Qualcomm RB5** | `sudo ./setup.sh` | Full hardware config via setup_rb5.sh |
| **Raspberry Pi 3/4/5** | `sudo ./setup.sh` | Lite or Desktop OS |
| **NVIDIA Jetson** | `sudo ./setup.sh` | CUDA/TensorRT auto-detected |

---

## Author and License

**Author:** Sudheer Ibrahim Daniel Devu ([SID-Devu](https://github.com/SID-Devu))

**License:** MIT - See [LICENSE](LICENSE) file

**Version:** 1.3.0
**Released:** February 2026

---

## Contributing

Want to improve the system? Contributions welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and commit: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## Support

Having issues? Check the **Troubleshooting** section above.

For bugs or feature requests, open an issue on GitHub: [Issues](https://github.com/SID-Devu/reception-camera/issues)
