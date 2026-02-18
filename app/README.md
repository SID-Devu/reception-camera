# Reception Greeter

**Production-ready reception camera system** that detects people entering/leaving,
recognizes them by face, and greets them by name using text-to-speech.

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

## Project Structure

```
reception-camera/
  app/
    main.py              # Main real-time pipeline
    config.yaml          # All configuration
    vision/
      camera.py          # Threaded camera capture
      face_detect.py     # Face detection (InsightFace)
      embedder.py        # Embedding extraction + normalisation
      matcher.py         # Cosine similarity matching
      tracker.py         # Centroid-based face tracker
      events.py          # Door-line crossing event detection
    audio/
      tts.py             # Text-to-speech (pyttsx3, background thread)
    db/
      schema.sql         # SQLite schema
      storage.py         # Database operations
  tools/
    enroll.py            # Enrollment CLI
    admin.py             # Admin CLI (list, delete, events, stats)
    export_db.py         # Export/import face database
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
| `camera` | source (0=USB, RTSP URL), resolution, FPS |
| `face_detection` | confidence threshold, min face size, model pack |
| `recognition` | similarity threshold (0.35–0.50), consecutive frames |
| `tracking` | max link distance, frames before track deletion |
| `door_line` | orientation, position (fraction), inside direction |
| `greeting` | templates, cooldown seconds |
| `enrollment` | num samples, quality check thresholds |
| `tts` | engine, rate, volume |

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
