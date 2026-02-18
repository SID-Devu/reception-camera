from cv2 import VideoCapture, imwrite
import numpy as np

class CameraCapture:
    def __init__(self, camera_index=0, frame_width=640, frame_height=480):
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.camera = None

    def initialize_camera(self):
        self.camera = VideoCapture(self.camera_index)
        self.camera.set(3, self.frame_width)
        self.camera.set(4, self.frame_height)

    def capture_frame(self):
        if self.camera is None:
            raise Exception("Camera not initialized. Call initialize_camera() first.")
        
        ret, frame = self.camera.read()
        if not ret:
            raise Exception("Failed to capture frame from camera.")
        
        return frame

    def save_frame(self, frame, filename):
        imwrite(filename, frame)

    def release_camera(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None

if __name__ == "__main__":
    camera_capture = CameraCapture()
    camera_capture.initialize_camera()
    
    try:
        while True:
            frame = camera_capture.capture_frame()
            # Here you can add processing logic for the frame
            camera_capture.save_frame(frame, "captured_frame.jpg")
            # Break the loop after capturing one frame for demonstration
            break
    finally:
        camera_capture.release_camera()