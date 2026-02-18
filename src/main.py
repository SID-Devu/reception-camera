import cv2
from fastapi import FastAPI
from camera.capture import CameraCapture
from detection.face_detector import FaceDetector
from recognition.encoder import FaceEncoder
from recognition.matcher import FaceMatcher
from greeting.greeter import Greeter
from learning.incremental_trainer import IncrementalTrainer
from database.repository import DatabaseRepository
from config import settings

app = FastAPI()

camera = CameraCapture(settings.CAMERA_INDEX)
face_detector = FaceDetector()
face_encoder = FaceEncoder()
face_matcher = FaceMatcher()
greeter = Greeter()
incremental_trainer = IncrementalTrainer()
database_repository = DatabaseRepository()

@app.on_event("startup")
async def startup_event():
    camera.start()
    await database_repository.connect()

@app.on_event("shutdown")
async def shutdown_event():
    camera.stop()
    await database_repository.disconnect()

def recognition_loop():
    while True:
        frame = camera.get_frame()
        faces = face_detector.detect(frame)
        
        for face in faces:
            embedding = face_encoder.encode(face)
            match = face_matcher.match(embedding)
            
            if match:
                greeter.greet(match.name)
            else:
                greeter.greet("Guest")

if __name__ == "__main__":
    recognition_loop()