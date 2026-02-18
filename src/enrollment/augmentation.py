from torchvision import transforms
import numpy as np

class Augmentation:
    def __init__(self):
        self.transform = transforms.Compose([
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
            transforms.Resize((112, 112)),
            transforms.ToTensor(),
        ])

    def augment(self, image):
        return self.transform(image)

    def batch_augment(self, images):
        return [self.augment(image) for image in images]