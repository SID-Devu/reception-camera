from typing import List
import cv2

class FaceDetector:
    def __init__(self, model_path: str):
        self.model = cv2.dnn.readNetFromONNX(model_path)

    def detect_faces(self, image: List[int]) -> List[dict]:
        blob = cv2.dnn.blobFromImage(image, 1.0, (640, 640), (104.0, 177.0, 123.0), swapRB=True, crop=False)
        self.model.setInput(blob)
        detections = self.model.forward()

        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:  # Confidence threshold
                box = detections[0, 0, i, 3:7] * np.array([image.shape[1], image.shape[0], image.shape[1], image.shape[0]])
                (startX, startY, endX, endY) = box.astype("int")
                faces.append({"box": (startX, startY, endX, endY), "confidence": confidence})

        return faces