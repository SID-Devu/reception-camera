import pytest
from src.detection.face_detector import FaceDetector

@pytest.fixture
def face_detector():
    return FaceDetector()

def test_face_detection_valid_image(face_detector):
    image = "path/to/valid/image.jpg"  # Replace with a valid image path
    detections = face_detector.detect(image)
    assert len(detections) > 0  # Ensure at least one face is detected

def test_face_detection_invalid_image(face_detector):
    image = "path/to/invalid/image.jpg"  # Replace with an invalid image path
    detections = face_detector.detect(image)
    assert len(detections) == 0  # Ensure no faces are detected

def test_face_detection_multiple_faces(face_detector):
    image = "path/to/multiple_faces.jpg"  # Replace with an image with multiple faces
    detections = face_detector.detect(image)
    assert len(detections) > 1  # Ensure multiple faces are detected

def test_face_detection_empty_image(face_detector):
    image = "path/to/empty/image.jpg"  # Replace with an empty image path
    detections = face_detector.detect(image)
    assert len(detections) == 0  # Ensure no faces are detected in an empty image