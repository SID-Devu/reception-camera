from PIL import Image
import numpy as np

class Preprocessor:
    def __init__(self, target_size=(112, 112)):
        self.target_size = target_size

    def preprocess(self, image):
        image = self.resize_image(image)
        image = self.normalize_image(image)
        return image

    def resize_image(self, image):
        return image.resize(self.target_size, Image.ANTIALIAS)

    def normalize_image(self, image):
        image_array = np.asarray(image)
        image_array = image_array / 255.0  # Normalize to [0, 1]
        return image_array.astype(np.float32)  # Convert to float32 for model input