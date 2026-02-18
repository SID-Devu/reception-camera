from recognition.encoder import Encoder
import pytest

class TestEncoder:
    def setup_method(self):
        self.encoder = Encoder()

    def test_embedding_extraction(self):
        test_image = "path/to/test/image.jpg"  # Replace with a valid image path
        embedding = self.encoder.extract_embedding(test_image)
        assert embedding is not None
        assert len(embedding) == self.encoder.embedding_size  # Assuming encoder has an attribute for embedding size

    def test_embedding_shape(self):
        test_image = "path/to/test/image.jpg"  # Replace with a valid image path
        embedding = self.encoder.extract_embedding(test_image)
        assert embedding.shape == (self.encoder.embedding_size,)

    def test_invalid_image(self):
        invalid_image = "path/to/invalid/image.jpg"  # Replace with an invalid image path
        with pytest.raises(ValueError):
            self.encoder.extract_embedding(invalid_image)