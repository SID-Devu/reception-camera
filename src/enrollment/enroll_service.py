from datetime import datetime
import os
import cv2
import numpy as np
from database.repository import Repository
from recognition.encoder import Encoder
from utils.logger import get_logger

logger = get_logger(__name__)

class EnrollmentService:
    def __init__(self, db_repository: Repository, encoder: Encoder):
        self.db_repository = db_repository
        self.encoder = encoder

    def enroll(self, person_name: str, capture_count: int = 5):
        logger.info(f"Starting enrollment for {person_name}")
        if self.db_repository.exists(person_name):
            logger.warning(f"{person_name} is already enrolled.")
            return False

        face_samples = self.capture_face_samples(capture_count)
        if not face_samples:
            logger.error("No face samples captured.")
            return False

        embeddings = self.encoder.encode(face_samples)
        self.db_repository.save_embeddings(person_name, embeddings)
        logger.info(f"Enrollment successful for {person_name}")
        return True

    def capture_face_samples(self, count: int):
        logger.info("Initializing camera for face capture")
        camera = cv2.VideoCapture(0)
        samples = []
        captured = 0

        while captured < count:
            ret, frame = camera.read()
            if not ret:
                logger.error("Failed to capture image from camera.")
                break

            face = self.detect_face(frame)
            if face is not None:
                samples.append(face)
                captured += 1
                logger.info(f"Captured sample {captured}/{count}")

        camera.release()
        return samples

    def detect_face(self, frame):
        # Placeholder for face detection logic
        # This should return the detected face region
        return frame  # Replace with actual face detection logic

    def save_enrollment_log(self, person_name: str):
        log_entry = f"{datetime.now()}: Enrolled {person_name}\n"
        with open("enrollment_log.txt", "a") as log_file:
            log_file.write(log_entry)

# Example usage:
# db_repo = Repository()
# encoder = Encoder()
# enroll_service = EnrollmentService(db_repo, encoder)
# enroll_service.enroll("John Doe")