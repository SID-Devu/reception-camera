import time
import cv2
import numpy as np
from src.recognition.encoder import Encoder
from src.recognition.matcher import Matcher
from src.utils.metrics import Metrics

class Benchmark:
    def __init__(self, video_source=0):
        self.video_source = video_source
        self.encoder = Encoder()
        self.matcher = Matcher()
        self.metrics = Metrics()
        self.cap = cv2.VideoCapture(self.video_source)

    def run_benchmark(self, num_frames=100):
        total_time = 0
        for _ in range(num_frames):
            start_time = time.time()
            ret, frame = self.cap.read()
            if not ret:
                break

            # Simulate face detection and recognition
            faces = self.detect_faces(frame)
            for face in faces:
                embedding = self.encoder.encode(face)
                self.matcher.match(embedding)

            total_time += time.time() - start_time

        self.cap.release()
        avg_time_per_frame = total_time / num_frames
        print(f"Average time per frame: {avg_time_per_frame:.4f} seconds")

    def detect_faces(self, frame):
        # Placeholder for face detection logic
        # In a real implementation, this would use a face detection model
        return [frame]  # Simulating one detected face

if __name__ == "__main__":
    benchmark = Benchmark()
    benchmark.run_benchmark()