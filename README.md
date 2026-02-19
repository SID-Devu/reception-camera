# Reception Greeter

Real-time face-recognition camera system that **greets people by name** when they arrive and **says goodbye** when they leave. Designed for office receptions, lobbies, and front-desk environments.

**What it does:**
```
Your Camera → Detects Faces → Recognizes People → Plays Audio Greeting
"Hey Alice, welcome! Have a nice day!"
```

---

## 🎯 Quick Overview

| Feature | What It Means |
|---------|---------------|
| **Face Detection** | Finds faces in camera feed (works in real-time) |
| **Recognition** | Matches faces to enrolled people by name |
| **Voice Greeting** | Speaks "Welcome Alice" automatically |
| **Goodbye Tracking** | Says goodbye when person leaves |
| **Database** | Saves who visited and when |
| **Works Offline** | No internet required after setup |

---

## ✅ Before You Start - Quick Checklist

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
python -c "import cv2; cap = cv2.VideoCapture(0); print('✅ Webcam works!' if cap.isOpened() else '❌ Webcam not found')"
```

---

## 📋 Prerequisites

| Item | Requirements | Notes |
|------|--------------|-------|
| **Python** | 3.10, 3.11, 3.12, or 3.13 | [Download Python](https://www.python.org/downloads/) |
| **Webcam** | Any USB or built-in camera | Must be recognized by your OS |
| **OS** | Windows 10/11, macOS, Linux | Fresh installation works on all |
| **Internet** | Needed first time only | ~500MB download for face models |

### For Different Laptop Types

| Laptop Type | What to Expect | Performance |
|------------|---|---|
| **New/Gaming Laptop** | Everything will work smoothly | ⚡ 30+ FPS, instant recognition |
| **Mid-range Laptop** | Runs well, slight delays possible | ⚡ 15-20 FPS |
| **Old Laptop (5+ years)** | Will work but slower | 🐢 5-10 FPS, might be sluggish |

> **For old laptops:** The system still works but may take 2-3 seconds to recognize someone. This is normal.

---

## 🚀 Installation (For Everyone)

**Estimated time:** 10-15 minutes (depending on your internet speed)

### Step 1: Clone the Repository

```bash
git clone https://github.com/SID-Devu/reception-camera.git
cd reception-camera
```

Expected output:
```
Cloning into 'reception-camera'...
✓ Cloned successfully to your computer
```

### Step 2: Check Your Python Installation

```bash
# Should show 3.10 or higher
python --version
```

Expected output:
```
Python 3.12.3
```

> **Doesn't show version?** [Install Python here](https://www.python.org/downloads/)

### Step 3: Create a Virtual Environment (Isolated Python)

A virtual environment keeps this project separate from other Python projects on your laptop.

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

Expected output:
```
(.venv) C:\Users\YourName\reception-camera>
```

> Note: `(.venv)` at the start shows the virtual environment is active.

### Step 4: Install All Dependencies

**Windows users** - Run this (easiest, handles build issues automatically):

```bash
python install.py
```

**Everyone else:**

```bash
pip install --prefer-binary opencv-python numpy insightface onnxruntime scipy pyttsx3 PyYAML albumentations==1.4.24
```

Expected output:
```
Collecting opencv-python
  Downloading opencv_python-4.13.0...
...
✅ Successfully installed insightface-0.7.3
```

> **Installation takes 2-5 minutes** depending on your internet. Be patient!

### Step 5: Download Face Recognition Models

This downloads the face recognition AI (~350MB) once. After this, it's stored locally and works offline.

```bash
python tools/download_models.py
```

Expected output:
```
✅ Models downloaded and cached successfully!
```

> **Note:** This might take 2-3 minutes on slow internet. Grab ☕ coffee!

### ✅ Setup Complete!

You're ready to use the system. Go to the next section based on what you want to do.

---

## 👨‍💼 For Engineers: Testing & Development

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

**Expected output:**
```
✅ Enrolled Alice with 15 samples (quality: 95%)
```

### Verify It Works

**Test 1: See who's in the database**

```bash
python tools/admin.py --config app/config.yaml list
```

Expected output:
```
Enrolled people:
  1. Alice    (15 samples, quality 95%)
  2. Bob      (18 samples, quality 98%)
```

**Test 2: See recent greetings**

```bash
python tools/admin.py --config app/config.yaml events --last 10
```

Expected output:
```
2025-02-19 14:30:22 - ENTRY - Alice
2025-02-19 14:30:30 - EXIT  - Alice
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

## 🧪 For Manual Testers: Testing Checklist

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

#### Test 1: Basic Entry Greeting ✅
- [ ] Face appears in camera →
- [ ] System shows bounding box →
- [ ] Hears: "Hey Alice, welcome! Have a nice day."

**Expected behavior:** Greeting plays in 3-5 seconds

**If it fails:**
- Check system volume is not muted
- Move closer to camera
- Check microphone/speakers are connected

#### Test 2: Exit/Goodbye Greeting ✅
- [ ] Greeted person looks away →
- [ ] Wait 3-5 seconds →
- [ ] Hears: "Bye Alice, see you later!"

**Expected behavior:** Goodbye plays when leaving camera view

**If it fails:**
- Make sure person was fully recognized (check bounding box)
- Wait 5+ seconds before testing goodbye
- Check system volume

#### Test 3: Multiple People at Once ✅
- [ ] Put 2-3 faces in camera →
- [ ] Should recognize all simultaneously →
- [ ] Should hear all greetings in sequence

**Expected behavior:** All recognized people are greeted within 5 seconds

#### Test 4: Old Laptop Test (if available) ✅
- [ ] Run on older machine
- [ ] Should see live feed (might be slower)
- [ ] Recognition should work (5-20 seconds acceptable)
- [ ] All features should function

**Note:** Older laptops are 5-10x slower. This is normal and acceptable.

#### Test 5: Repeated Recognition (Cooldown) ✅
- [ ] Greet Alice
- [ ] Alice leaves
- [ ] Alice comes back within 5 minutes
- [ ] Should NOT greet again (5-minute cooldown)
- [ ] After 5 minutes, should greet again

**Expected behavior:** Respects cooldown timer to avoid spam

#### Test 6: Database Persistence ✅
- [ ] Check people list: `python tools/admin.py list`
- [ ] Stop system (Ctrl+C)
- [ ] Start system again
- [ ] People list should be identical

**Expected behavior:** All data survives restart

### Test Results Template

```
System:        Windows 10 / macOS / Linux
Laptop:        New / Mid-range / Old
Python:        3.12.3
Date:          2025-02-19

Test 1 - Entry Greeting:    ✅ PASS / ❌ FAIL
Test 2 - Exit Greeting:     ✅ PASS / ❌ FAIL
Test 3 - Multiple People:   ✅ PASS / ❌ FAIL
Test 4 - Old Laptop:        ✅ PASS / ❌ FAIL
Test 5 - Cooldown:          ✅ PASS / ❌ FAIL
Test 6 - Database:          ✅ PASS / ❌ FAIL

Issues Found:
- (none) / list here
```

---

## 🛠️ Troubleshooting

### "Webcam not found" or "Camera won't open"

```bash
# Check if camera device exists
python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'NOT FOUND')"
```

**Solutions:**
- [ ] Reconnect USB webcam (if using external)
- [ ] Restart program
- [ ] Try different USB port
- [ ] In `app/config.yaml`, change `source: 0` to `source: 1` (if multiple cameras)

### "No sound / greeting not playing"

```bash
# Check volume
python -c "import pyttsx3; e = pyttsx3.init(); e.say('test'); e.runAndWait()"
```

**Solutions:**
- [ ] Check system volume is on
- [ ] Unmute speakers
- [ ] Check `app/config.yaml` - `tts.volume: 0.9`
- [ ] **macOS:** System volume controls output (set to 50%+ in System Preferences)
- [ ] **Linux:** Install espeak: `sudo apt install espeak`

### "Face not recognized"

**Solutions:**
- [ ] Improve lighting (move closer to window or light)
- [ ] Re-enroll person with better samples
- [ ] Increase max samples: `python tools/enroll.py --name "Person" --min-samples 20`
- [ ] Lower similarity threshold in `app/config.yaml`: `similarity_threshold: 0.35`

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

## 📖 Full Commands Reference

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
python tools/admin.py list --config app/config.yaml

# Show person details
python tools/admin.py info --name "Alice" --config app/config.yaml

# Delete person
python tools/admin.py delete --name "Alice" --config app/config.yaml

# See recent events
python tools/admin.py events --last 50 --config app/config.yaml

# See statistics
python tools/admin.py stats --config app/config.yaml
```

### Database

```bash
# Backup database to JSON
python tools/export_db.py export backup.json --config app/config.yaml

# Restore database from JSON
python tools/export_db.py import backup.json --config app/config.yaml
```

---

## ⚙️ Configuration (For Advanced Users)

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

```bash
# GUI mode - shows camera preview, captures face samples
python tools/enroll.py --config app/config.yaml --name "Alice"

# Headless mode (e.g. SSH / no monitor)
python tools/enroll.py --config app/config.yaml --name "Alice" --no-display
```

The tool captures 10-20 face samples with quality checks (blur, pose, brightness)
and stores 512-dim ArcFace embeddings in `data/faces.db`.

### 7. Run the greeter

```bash
python app/main.py --config app/config.yaml
```

A window opens showing the camera feed with bounding boxes. When a recognised
person appears:

- **ENTRY:** "Hey Alice, welcome! Have a nice day."
- **EXIT:** "Bye Alice, see you later!" (when face leaves view)

**Hotkeys in the display window:**

| Key | Action |
|-----|--------|
| `q` | Quit (says goodbye first) |
| `r` | Hot-reload face database after new enrollment |

---

## 📚 How It Works (Technical Details)

### The Processing Pipeline

```
Your Camera
    ↓
Frame arrives at 30 FPS
    ↓
Every 3rd frame, detect faces using SCRFD
    ↓
For each face, extract ArcFace feature (512-dim vector)
    ↓
Compare against database of known faces (cosine similarity)
    ↓
Track faces across frames using centroid distance
    ↓
When streak reaches 3 frames: Fire ENTRY event → Play greeting audio
    ↓
When face leaves frame: Fire EXIT event → Play goodbye audio
```

### Key Components

- **Face Detection:** SCRFD model (fast, runs on CPU)
- **Face Recognition:** ArcFace embeddings (512-dimensional vectors)
- **Tracking:** Centroid-based tracking with streak counting
- **Audio:** Background thread TTS engine (doesn't block vision)
- **Database:** SQLite stores faces, embeddings, and visit events

---

## 🔧 Advanced Configuration

See `app/config.yaml` for full settings. Common tuning parameters:

| Setting | What It Does | Default | Tip |
|---------|------------|---------|-----|
| `similarity_threshold` | How strict face matching is | 0.40 | Lower (0.30) = more lenient |
| `consecutive_frames_required` | Frames before greeting | 3 | Lower = faster greeting |
| `max_frames_missing` | Frames before EXIT event | 8 | Lower = faster goodbye |
| `min_face_size` | Minimum face pixel width | 60 | Lower = detects distant faces |
| `cooldown_seconds` | Time before re-greeting | 300 | Set to 0 to always greet |

---

## 🏗️ Architecture

```
reception-camera/
├── app/                      # Main application
│   ├── main.py              # Entry point (vision pipeline)
│   ├── config.yaml          # All settings
│   ├── audio/
│   │   └── tts.py           # Text-to-speech engine (background thread)
│   ├── db/
│   │   ├── storage.py       # SQLite database access
│   │   └── schema.sql       # Database schema
│   └── vision/
│       ├── camera.py        # Camera reader (background thread)
│       ├── face_detect.py   # SCRFD face detector
│       ├── embedder.py      # ArcFace embedding extractor
│       ├── matcher.py       # Cosine similarity matcher
│       ├── tracker.py       # Centroid tracker
│       └── events.py        # ENTRY/EXIT event detector
├── tools/                    # Utility scripts
│   ├── enroll.py            # Enrol new person
│   ├── admin.py             # Manage database
│   └── download_models.py   # Download AI models
├── data/                     # Stores database
├── logs/                     # Stores logs
└── README.md                # This file
```

---

## 📋 Author & License

**Author:** Sudheer Ibrahim Daniel Devu ([SID-Devu](https://github.com/SID-Devu))

**License:** MIT - See [LICENSE](LICENSE) file

**Version:** 1.1.0  
**Released:** February 2026

---

## 🤝 Contributing

Want to improve the system? Contributions welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and commit: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📞 Support

Having issues? Check the **Troubleshooting** section above. 

For bugs or feature requests, open an issue on GitHub: [Issues](https://github.com/SID-Devu/reception-camera/issues)
