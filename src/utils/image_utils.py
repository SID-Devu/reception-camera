def resize_image(image, target_size):
    from PIL import Image
    return image.resize(target_size, Image.ANTIALIAS)

def normalize_image(image):
    import numpy as np
    return (np.array(image) / 255.0).astype(np.float32)

def convert_to_rgb(image):
    if image.mode != 'RGB':
        return image.convert('RGB')
    return image

def preprocess_image(image, target_size=(224, 224)):
    image = convert_to_rgb(image)
    image = resize_image(image, target_size)
    image = normalize_image(image)
    return image

def save_image(image, path):
    image.save(path)