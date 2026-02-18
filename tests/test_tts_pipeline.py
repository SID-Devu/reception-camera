"""
Full end-to-end test: Camera → Detection → Recognition → Presence Events → TTS.

Phase 1: Detect face, recognise Sudheer, speak entry greeting.
Phase 2: Simulate face leaving, speak exit goodbye.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import cv2
import numpy as np
from app.db.storage import FaceDB
from app.vision.face_detect import FaceDetector
from app.vision.embedder import Embedder
from app.vision.matcher import FaceMatcher
from app.vision.tracker import CentroidTracker
from app.vision.events import PresenceEventDetector, EventType
from app.audio.tts import TTSEngine

with open("app/config.yaml") as f:
    config = yaml.safe_load(f)

db_path = os.path.normpath(os.path.join("app", config["database"]["path"]))
db = FaceDB(db_path)

detector = FaceDetector(
    model_pack="buffalo_l", min_confidence=0.5,
    min_face_size=60, detection_resize_width=640, use_gpu=False,
)
embedder = Embedder()
matcher = FaceMatcher(similarity_threshold=0.40)
matcher.reload(db)
tracker = CentroidTracker(max_link_distance=120, max_frames_missing=8)
presence = PresenceEventDetector(cooldown_seconds=300, consecutive_frames_required=3)
tts = TTSEngine(rate=170, volume=0.9)

entry_tpl = config["greeting"]["entry_template"]
exit_tpl = config["greeting"]["exit_template"]

print("=== FULL TTS PIPELINE TEST ===\n")

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
time.sleep(0.5)

# ---- Phase 1: Face visible → ENTRY ----
print("Phase 1: Detecting face and greeting...")
entry_fired = False
for frame_idx in range(25):
    ret, frame = cap.read()
    if not ret:
        continue
    if frame_idx % 3 == 0:
        faces = detector.detect(frame)
        faces = embedder.extract(faces)
        detections = [(f.center, f.bbox) for f in faces]
        tracks, lost = tracker.update(detections)
        for track in tracks:
            best_face = min(
                faces,
                key=lambda f: np.linalg.norm(
                    np.array(f.center) - np.array(track.center)
                ),
                default=None,
            )
            if best_face and best_face.embedding is not None:
                result = matcher.match(best_face.embedding)
                if result:
                    track.update_identity(result.person_id, result.name, result.similarity)
                else:
                    track.update_identity(None, "Unknown", 0.0)
        events = presence.check_tracks(tracks, lost)
        for ev in events:
            if ev.event_type == EventType.ENTRY:
                msg = entry_tpl.format(name=ev.name)
                entry_fired = True
            else:
                msg = exit_tpl.format(name=ev.name)
            print(f'  >>> {ev.event_type.value.upper()}: Speaking: "{msg}"')
            tts.speak(msg)
            db.log_event(ev.event_type.value, ev.person_id, ev.name, ev.similarity)

if not entry_fired:
    print("  [WARN] No ENTRY event fired. Face might not be visible.")

# ---- Phase 2: Face disappears → EXIT ----
print("\nPhase 2: Simulating departure...")
exit_fired = False
for frame_idx in range(20):
    tracks, lost = tracker.update([])
    events = presence.check_tracks(tracks, lost)
    for ev in events:
        msg = exit_tpl.format(name=ev.name)
        print(f'  >>> {ev.event_type.value.upper()}: Speaking: "{msg}"')
        tts.speak(msg)
        db.log_event(ev.event_type.value, ev.person_id, ev.name, ev.similarity)
        exit_fired = True
    time.sleep(0.05)

if not exit_fired:
    print("  [WARN] No EXIT event fired.")

cap.release()

# Wait for TTS to finish
print("\nWaiting for TTS to finish speaking...")
tts.wait_and_shutdown()
db.close()

print("\n=== RESULTS ===")
print(f"  ENTRY event fired: {entry_fired}")
print(f"  EXIT event fired:  {exit_fired}")
if entry_fired and exit_fired:
    print("  STATUS: PASS - Both greetings spoken!")
else:
    print("  STATUS: PARTIAL - See warnings above")
print("\nFULL TTS PIPELINE TEST COMPLETE!")
