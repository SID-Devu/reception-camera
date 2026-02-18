from keras.models import load_model
import numpy as np

class FaceEncoder:
    def __init__(self, model_path):
        self.model = load_model(model_path)

    def encode(self, face_image):
        face_image = self.preprocess(face_image)
        embedding = self.model.predict(np.expand_dims(face_image, axis=0))
        return embedding.flatten()

    def preprocess(self, face_image):
        # Resize and normalize the image
        face_image = cv2.resize(face_image, (112, 112))  # Assuming the model expects 112x112 input
        face_image = face_image.astype('float32') / 255.0  # Normalize to [0, 1]
        return face_image

    def save_model(self, model_path):
        self.model.save(model_path)

    def load_model(self, model_path):
        self.model = load_model(model_path)