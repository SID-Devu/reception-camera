# Reception Greeter

Real-time face-recognition camera system that **greets people by name** when
they arrive and **says goodbye** when they leave. Designed for office
receptions, lobbies, and front-desk environments.

```
Camera → Face Detection → Embedding → Recognition → Tracking → Event → TTS
```

| Feature | Detail |
|---------|--------|
| Face detection | InsightFace SCRFD (640x640, CPU/GPU) |
| Recognition | ArcFace `w600k_r50` - 512-dim cosine similarity |
| Tracking | Centroid-distance tracker with identity streaks |
| Events | Presence-based or door-line crossing |
| TTS | Offline pyttsx3 (Windows SAPI / macOS AVFoundation / Linux espeak) |
| Database | SQLite - faces, embeddings, audit events |
| Cooldown | Configurable per-person cooldown (default 5 min) |

---

## Architecture

```
reception-camera/
├── app/                    # Production pipeline
│   ├── main.py             # Real-time pipeline entry point
│   ├── config.yaml         # All configuration
│   ├── audio/
│   │   └── tts.py          # pyttsx3 background TTS engine
│   ├── db/
│   │   ├── storage.py      # SQLite face database (CRUD + events)
│   │   └── schema.sql      # Schema reference
│   └── vision/
│       ├── camera.py       # Threaded camera reader
│       ├── face_detect.py  # InsightFace SCRFD detector
│       ├── embedder.py     # ArcFace embedding extractor
│       ├── matcher.py      # Vectorised cosine-similarity matcher
│       ├── tracker.py      # Centroid tracker with identity streaks
│       └── events.py       # Presence / door-line event detectors
├── tools/                  # CLI utilities
│   ├── enroll.py           # Enrol new people (camera or headless)
│   ├── admin.py            # List / delete / query people and events
│   └── export_db.py        # Export / import database to JSON
├── tests/
│   └── test_tts_pipeline.py # End-to-end ENTRY + EXIT test
├── data/                   # SQLite database (auto-created)
├── logs/                   # Log files (auto-created)
└── app/config.yaml         # Tuning knobs
```

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10 - 3.13 | Tested on 3.13 (Windows) |
| pip | latest | `python -m pip install --upgrade pip` |
| Webcam | any USB / built-in | Or RTSP URL in config |
| OS | Windows 10/11, Linux, macOS | TTS uses SAPI (Win), AVFoundation (macOS), or espeak (Linux) |

### Hardware

- **CPU-only** works at 10-15 FPS on a modern laptop.
- **GPU** (NVIDIA + CUDA): install `onnxruntime-gpu` for 30+ FPS.

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/sudhdevu/reception-camera.git
cd reception-camera
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install opencv-python numpy insightface onnxruntime scipy pyttsx3 PyYAML albumentations==1.4.24
```

> **Note:** `albumentations` must be pinned to 1.4.24 to avoid a known torch
> dependency hang on import. If you don't need enrollment augmentation you can
> skip it.

> **GPU users:** Replace `onnxruntime` with `onnxruntime-gpu` and set
> `performance.use_gpu: true` in `app/config.yaml`.

### 4. Download the face model (required)

**Download the model explicitly before first use:**

```bash
python tools/download_models.py
```

This pre-downloads the InsightFace `buffalo_l` model (~350MB) to avoid download issues on first run. 
On fresh machines, auto-download can fail due to network timeouts or cache permission issues.

**Note:** If the download fails, try:
- **Retry:** `python tools/download_models.py` again
- **Check network:** Ensure internet connectivity
- **Manual cache:** Set `INSIGHTFACE_HOME` environment variable to an existing directory: 
  ```bash
  $env:INSIGHTFACE_HOME = "C:\path\to\models"
  python tools/download_models.py
  ```

### 6. Enrol a person

InsightFace downloads the `buffalo_l` model pack on first run. It is cached at:

- **Windows:** `C:\Users\<you>\.insightface\models\buffalo_l\`
- **Linux:** `~/.insightface/models/buffalo_l/`

No manual download is needed.

### 5. Enrol a person

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

**CLI flags:**

| Flag | Description |
|------|-------------|
| `--no-display` | Run headless (no GUI window) |
| `--no-tts` | Disable audio greetings |
| `--config PATH` | Path to YAML config file |

---

## Admin Tools

### List enrolled people

```bash
python tools/admin.py --config app/config.yaml list
```

### Show person details

```bash
python tools/admin.py --config app/config.yaml info --name "Alice"
```

### View recent events

```bash
python tools/admin.py --config app/config.yaml events --last 20
```

### View statistics

```bash
python tools/admin.py --config app/config.yaml stats
```

### Delete a person

```bash
python tools/admin.py --config app/config.yaml delete --name "Alice"
```

### Export / import database

```bash
# Export to JSON (includes base64-encoded embeddings)
python tools/export_db.py --config app/config.yaml export backup.json

# Import from JSON
python tools/export_db.py --config app/config.yaml import backup.json
```

---

## Configuration Reference

All settings live in `app/config.yaml`:

### Camera

```yaml
camera:
  source: 0                     # USB device index or RTSP URL
  width: 1280
  height: 720
  fps: 30
  detect_every_n_frames: 3      # Skip N-1 frames between detections
```

### Face Detection

```yaml
face_detection:
  min_confidence: 0.5           # Detection confidence threshold
  min_face_size: 60             # Minimum face width in pixels
  model_pack: "buffalo_l"       # InsightFace model pack
```

### Recognition

```yaml
recognition:
  similarity_threshold: 0.40    # Cosine similarity threshold (0.25-0.55)
  consecutive_frames_required: 3 # Require N consecutive matches before greeting
```

### Tracking

```yaml
tracking:
  max_link_distance: 120        # Max pixel distance to link detections
  max_frames_missing: 8         # Frames before track is considered lost
```

### Greeting

```yaml
greeting:
  mode: "presence"              # "presence" or "door_line"
  cooldown_seconds: 300         # Don't re-greet within this time
  entry_template: "Hey {name}, welcome! Have a nice day."
  exit_template: "Bye {name}, see you later!"
```

### TTS

```yaml
tts:
  engine: "pyttsx3"             # Offline TTS (Windows SAPI / macOS AVFoundation / Linux espeak)
  rate: 170                     # Words per minute (adjusted for each platform)
  volume: 0.9                   # 0.0 - 1.0 (system volume controls output on macOS)
```

### Performance

```yaml
performance:
  detection_resize_width: 640   # Resize frame for detection (0 = no resize)
  use_gpu: false                # Use CUDA if available
```

---

## How It Works

### Detection & Recognition Pipeline

1. **Camera** reads frames at 30 FPS in a background thread.
2. Every 3rd frame, **SCRFD** detects faces (resized to 640px for speed).
3. **ArcFace** extracts a 512-dimensional embedding per face.
4. **FaceMatcher** computes cosine similarity against all enrolled embeddings
   (vectorised NumPy operation - handles thousands of embeddings).
5. **CentroidTracker** assigns stable IDs across frames using centroid distance.
   Each track maintains an `identity_streak` counter.

### Event System

**Presence mode** (default):

- **ENTRY** fires when `identity_streak >= consecutive_frames_required`
  (person recognised for 3+ consecutive detection frames).
- **EXIT** fires when the track is lost (face leaves camera view for
  `max_frames_missing` detection cycles).
- On pipeline shutdown, forced goodbye fires for anyone still visible.

**Door-line mode** (optional):

- A virtual line is drawn across the frame.
- ENTRY/EXIT fire when a tracked face crosses the line in either direction.

### Text-to-Speech

- **pyttsx3** runs in a dedicated background thread.
- Speech is queued and processed sequentially (never blocks the vision loop).
- On Windows, uses SAPI5; on Linux, uses espeak.
- Engine is reinitialised per utterance to work around a known Windows COM bug.

---

## Troubleshooting

### Camera won't open

- Check that no other application is using the camera.
- Try a different `camera.source` value (0, 1, 2...).
- For RTSP streams: `camera.source: "rtsp://user:pass@ip:port/stream"`

### Model download fails on first run

- **Retry:** Run `python tools/download_models.py` again
- **Network issue:** Check internet connectivity (proxy, VPN, firewall)
- **Manual cache:** 
  ```bash
  $env:INSIGHTFACE_HOME = "C:\path\to\models"
  python tools/download_models.py
  ```
- **Timeout:** If download times out (>10 min), try on a faster connection
- **Space:** Ensure 500MB free disk space (~350MB for model + overhead)

### Face not detected

- Ensure face is at least 60px wide in the frame (adjust `min_face_size`).
- Check lighting - avoid extreme backlighting.
- Lower `min_confidence` to 0.3 for difficult conditions.

### Person not recognised

- Re-enrol with better lighting / angles.
- Lower `similarity_threshold` (try 0.35 or 0.30).
- Check enrollment quality: `python tools/admin.py --config app/config.yaml info --name "Alice"`

### TTS not playing audio

- Check system volume and default audio output device.
- **Windows:** Ensure no other apps override SAPI volume.
- **macOS:** 
  - System volume controls TTS output (volume property ignored by AVFoundation).
  - Check System Preferences → Sound → Output.
  - Test TTS independently: `python -c "import pyttsx3; e=pyttsx3.init(); e.say('hello'); e.runAndWait()"`
  - For debugging, run: `python test_macos_tts.py` (requires webcam folder)
- **Linux:** Install espeak (`sudo apt install espeak`) and pyttsx3 will use it automatically.

### Greeting fires too slowly / too fast

- **Faster ENTRY:** Lower `consecutive_frames_required` to 2.
- **Faster EXIT:** Lower `max_frames_missing` to 5.
- **Less frequent detection:** Increase `detect_every_n_frames`.

### albumentations import hangs

- Pin to version 1.4.24: `pip install albumentations==1.4.24`
- This avoids a torch dependency issue in newer versions.

---

## Running Tests

```bash
# Full ENTRY + EXIT pipeline test (requires webcam)
python tests/test_tts_pipeline.py
```

---

## Author

**Sudheer Ibrahim Daniel Devu** ([SID-Devu](https://github.com/SID-Devu))

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 Sudheer Ibrahim Daniel Devu

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request.
