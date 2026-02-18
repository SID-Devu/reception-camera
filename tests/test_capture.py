import pytest
from src.camera.capture import CameraCapture

@pytest.fixture
def camera_capture():
    capture = CameraCapture()
    yield capture
    capture.release()

def test_initialize_camera(camera_capture):
    assert camera_capture.is_initialized() is True

def test_capture_frame(camera_capture):
    frame = camera_capture.capture_frame()
    assert frame is not None
    assert frame.shape[0] > 0
    assert frame.shape[1] > 0

def test_release_camera(camera_capture):
    camera_capture.release()
    assert camera_capture.is_initialized() is False