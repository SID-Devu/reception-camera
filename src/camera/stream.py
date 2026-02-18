from camera.capture import CameraCapture
from detection.face_detector import FaceDetector
from recognition.encoder import Encoder
from recognition.matcher import Matcher
from utils.logger import Logger

class StreamManager:
    def __init__(self):
        self.camera = CameraCapture()
        self.face_detector = FaceDetector()
        self.encoder = Encoder()
        self.matcher = Matcher()
        self.logger = Logger()

    def start_stream(self):
        self.camera.start()
        self.logger.info("Camera stream started.")

        while True:
            frame = self.camera.get_frame()
            if frame is not None:
                self.process_frame(frame)

    def process_frame(self, frame):
        faces = self.face_detector.detect(frame)
        for face in faces:
            embedding = self.encoder.encode(face)
            recognized_person = self.matcher.match(embedding)
            if recognized_person:
                self.logger.info(f"Recognized: {recognized_person.name}")
                # Here you can add greeting logic
            else:
                self.logger.info("Unknown person detected.")

    def stop_stream(self):
        self.camera.stop()
        self.logger.info("Camera stream stopped.")