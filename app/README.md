# Reception Greeter

**Production-ready reception camera system** that detects people entering/leaving,
recognizes them by face, and greets them by name using text-to-speech.

**Now with hardware auto-detection** — plug in a Raspberry Pi, Qualcomm RB5,
any USB/CCTV camera, or speaker, and it automatically detects, configures, and runs.

## Features

- **Real-time face detection** using InsightFace (SCRFD / RetinaFace)
- **Face recognition** with ArcFace embeddings (high accuracy)
- **Person tracking** across frames with centroid-based tracker
- **Entry/exit detection** via virtual door-line crossing
- **Text-to-speech greetings** (offline via pyttsx3)
- **Enrollment tool** with quality checks (blur, pose, brightness)
- **Admin CLI** for managing persons and viewing events
- **SQLite database** for embeddings and audit trail
- **Hot-reload** support (press 'r' to reload after new enrollment)
- **Cooldown logic** to prevent repeated greetings
- **Privacy-friendly**: local processing, consent model, data retention

### Hardware Auto-Detection (NEW)

- **Platform detection**: Raspberry Pi 3/4/5, Qualcomm RB5, NVIDIA Jetson, x86
- **Camera auto-discovery**: USB cameras, CSI ribbon cameras (RPi/RB5), RTSP/CCTV network cameras
- **Speaker auto-detection**: USB speakers, HDMI audio, Bluetooth, built-in
- **Performance auto-tuning**: lighter models for RPi, QNN/DSP acceleration on RB5
- **Auto-reconnect**: camera auto-reconnects if disconnected
- **GStreamer support**: hardware-accelerated capture on ARM platforms
- **Thermal monitoring**: reduces workload if device overheats

## Supported Hardware

| Platform | Camera | Audio | Acceleration |
|----------|--------|-------|--------------|
| **Raspberry Pi 3** | USB, CSI (PiCamera) | HDMI, USB, 3.5mm | CPU (buffalo_s) |
| **Raspberry Pi 4/5** | USB, CSI (PiCamera v2/v3) | HDMI, USB, 3.5mm, I2S DAC | CPU (buffalo_s/l) |
| **Qualcomm RB5** | USB, MIPI-CSI | USB, HDMI | QNN NPU, Hexagon DSP |
| **NVIDIA Jetson** | USB, CSI | USB, HDMI | CUDA GPU |
| **x86 Desktop** | USB, RTSP/CCTV | Any | CUDA GPU or CPU |

## Quick Start

### 1. Install dependencies

```bash
cd reception-camera
pip install -r app/requirements.txt
```

### 2. Enroll yourself

```bash
python tools/enroll.py --name "Sudheer" --config app/config.yaml
```

Look at the camera. The tool captures 20 quality-checked face samples.
Slowly turn your head left/right for variety.

### 3. Run the pipeline

```bash
python app/main.py --config app/config.yaml
```

- Walk toward the camera → **"Hey Sudheer, welcome! Have a nice day."**
- Walk away → **"Bye Sudheer, see you later!"**
- Press **q** to quit, **r** to hot-reload the face database.

### Run on Raspberry Pi / Qualcomm RB5

```bash
# One-time setup (installs deps, creates systemd service)
sudo ./scripts/setup_edge_device.sh

# Or run manually with auto-detected config
python app/main.py --config app/config_rpi.yaml    # Raspberry Pi
python app/main.py --config app/config_rb5.yaml    # Qualcomm RB5
```

### Hardware detection only (no camera start)

```bash
python app/main.py --detect-only
```

This prints detected platform, cameras, speakers, and recommended settings.

## Project Structure

```
reception-camera/
  app/
    main.py              # Main real-time pipeline (with hardware auto-detection)
    config.yaml          # Default configuration (auto-tuned at startup)
    config_rpi.yaml      # Raspberry Pi optimised config
    config_rb5.yaml      # Qualcomm RB5 optimised config
    hardware/
      __init__.py        # Hardware module exports
      detector.py        # Platform / CPU / GPU / RAM detection
      camera_discovery.py  # USB, CSI, RTSP camera scanner
      audio_discovery.py   # Speaker / audio output scanner
    vision/
      camera.py          # Threaded camera capture (+ GStreamer, auto-reconnect)
      face_detect.py     # Face detection (InsightFace, multi-provider)
      embedder.py        # Embedding extraction + normalisation
      matcher.py         # Cosine similarity matching
      tracker.py         # Centroid-based face tracker
      events.py          # Door-line crossing event detection
    audio/
      tts.py             # Text-to-speech (auto-detect speaker, graceful fallback)
    db/
      schema.sql         # SQLite schema
      storage.py         # Database operations
  tools/
    enroll.py            # Enrollment CLI
    admin.py             # Admin CLI (list, delete, events, stats)
    export_db.py         # Export/import face database
  scripts/
    setup_edge_device.sh # One-command RPi/RB5 setup (deps + systemd service)
  data/
    faces.db             # SQLite database (auto-created)
  logs/
    reception.log        # Application log
    audit.log            # Entry/exit audit trail
```

## Configuration

Edit `app/config.yaml` to tune:

| Section | Key Settings |
|---------|-------------|
| `camera` | source (0=USB, RTSP URL, **"auto"**), resolution, FPS, GStreamer |
| `face_detection` | confidence threshold, min face size, model pack |
| `recognition` | similarity threshold (0.35–0.50), consecutive frames |
| `tracking` | max link distance, frames before track deletion |
| `door_line` | orientation, position (fraction), inside direction |
| `greeting` | templates, cooldown seconds |
| `enrollment` | num samples, quality check thresholds |
| `tts` | engine, rate, volume, **auto_detect_speaker** |
| `performance` | detection resize, use_gpu, **providers list** |
| `hardware` | **auto_detect**, scan_network_cameras, rtsp_urls |

## Admin Commands

```bash
# List enrolled persons
python tools/admin.py list

# Show person details
python tools/admin.py info --name "Sudheer"

# Delete a person
python tools/admin.py delete --name "Sudheer"

# View recent events
python tools/admin.py events --limit 20 --type entry

# System stats
python tools/admin.py stats

# Export database for backup
python tools/export_db.py export --output backup.json

# Import from backup
python tools/export_db.py import --input backup.json
```

## Accuracy Tips

- Enroll with **20+ samples** in the same camera/lighting
- Face the camera, then slowly turn head left/right during enrollment
- Tune `similarity_threshold` in config (start at 0.40, lower = stricter)
- `consecutive_frames_required: 3` prevents false-positive triggers
- Good lighting + 1080p camera = best results

## Privacy

- All processing is **local** (no cloud APIs)
- Embeddings stored in local SQLite (not reversible to photos)
- Visible notice recommended: "Face recognition in use"
- Instant deletion via admin tool
- Configurable data retention
